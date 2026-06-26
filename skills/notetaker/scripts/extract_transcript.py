#!/usr/bin/env python3
"""Extract a transcript from a local media file or an online video URL.

Subcommands
-----------
  check                 Report ffmpeg / openai-whisper / torch / yt-dlp / GPU availability.
  install               pip install -U the Python deps (openai-whisper, yt-dlp).
  media  <path>         Transcribe a local audio/video file with openai-whisper.
  url    <video-url>    Fetch captions via yt-dlp (no video download); fall back to
                        audio-only download + whisper when no captions are available.

Outputs (written into --out, default ./transcript_out)
------------------------------------------------------
  transcript.txt        Plain-text transcript.
  transcript.srt        Timestamped subtitles (whisper path, or converted captions).
  segments.json         Structured {start, end, text} segments (whisper path only).
  meta.json             Run metadata (source, model, device, language, path used).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus", ".wma"}
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv", ".m4v", ".wmv", ".ts"}


# --------------------------------------------------------------------------- #
# Environment probing
# --------------------------------------------------------------------------- #
def have_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def detect_gpu() -> dict:
    """Best-effort GPU detection. CUDA via torch is the only path whisper accelerates well."""
    info = {"cuda": False, "cuda_name": None, "mps": False, "nvidia_smi": have_cmd("nvidia-smi")}
    if module_available("torch"):
        try:
            import torch  # noqa: WPS433 (local import is intentional — torch is heavy/optional)

            info["cuda"] = bool(torch.cuda.is_available())
            if info["cuda"]:
                info["cuda_name"] = torch.cuda.get_device_name(0)
            info["mps"] = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        except Exception as exc:  # torch present but broken — report, don't crash
            info["torch_error"] = str(exc)
    return info


def environment_report() -> dict:
    return {
        "ffmpeg": have_cmd("ffmpeg"),
        "openai_whisper": module_available("whisper"),
        "torch": module_available("torch"),
        "yt_dlp": have_cmd("yt-dlp") or module_available("yt_dlp"),
        "gpu": detect_gpu(),
    }


def resolve_device(requested: str, gpu: dict) -> str:
    """Map --device {auto,cpu,cuda,mps} to an actual device, honouring the GPU policy."""
    if requested == "cpu":
        return "cpu"
    if requested == "cuda":
        if not gpu["cuda"]:
            raise SystemExit("Requested --device cuda but no CUDA device is available.")
        return "cuda"
    if requested == "mps":
        if not gpu["mps"]:
            raise SystemExit("Requested --device mps but Apple MPS is not available.")
        return "mps"
    # auto: prefer CUDA; never auto-select MPS (whisper's MPS path is unreliable).
    return "cuda" if gpu["cuda"] else "cpu"


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, check=check)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def write_outputs(out: Path, *, text: str, segments: list | None, srt: str | None, meta: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "transcript.txt").write_text(text.strip() + "\n", encoding="utf-8")
    if srt is not None:
        (out / "transcript.srt").write_text(srt, encoding="utf-8")
    if segments is not None:
        (out / "segments.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def segments_to_srt(segments: list[dict]) -> str:
    def stamp(seconds: float) -> str:
        if seconds < 0:
            seconds = 0.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    blocks = []
    for index, seg in enumerate(segments, start=1):
        blocks.append(str(index))
        blocks.append(f"{stamp(seg['start'])} --> {stamp(seg['end'])}")
        blocks.append(str(seg["text"]).strip())
        blocks.append("")
    return "\n".join(blocks)


# --------------------------------------------------------------------------- #
# FFmpeg + whisper
# --------------------------------------------------------------------------- #
def extract_audio_16k_mono(src: Path, out: Path) -> Path:
    require(have_cmd("ffmpeg"), "ffmpeg is not installed (see SKILL.md for install commands).")
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "audio_16k_mono.wav"
    run(["ffmpeg", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    return wav


def transcribe_with_whisper(audio: Path, *, model_name: str, device: str, language: str | None) -> dict:
    require(module_available("whisper"), "openai-whisper is not installed: pip install -U openai-whisper")
    import whisper  # local import: heavy, optional dependency

    print(f"loading whisper model '{model_name}' on {device} ...", file=sys.stderr)
    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(
        str(audio),
        language=language,
        fp16=(device == "cuda"),
        verbose=False,
    )
    return result


# --------------------------------------------------------------------------- #
# yt-dlp caption handling
# --------------------------------------------------------------------------- #
def ytdlp_cmd() -> list[str]:
    if have_cmd("yt-dlp"):
        return ["yt-dlp"]
    if module_available("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    raise SystemExit("yt-dlp is not installed: pip install -U yt-dlp")


def fetch_captions(url: str, out: Path, langs: str) -> Path | None:
    """Download human + auto captions as SRT, no video. Returns the chosen .srt or None."""
    out.mkdir(parents=True, exist_ok=True)
    template = str(out / "%(id)s.%(ext)s")
    run(
        ytdlp_cmd()
        + [
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            langs,
            "--convert-subs",
            "srt",
            "-o",
            template,
            url,
        ],
        check=False,
    )
    srts = sorted(out.glob("*.srt"))
    if not srts:
        return None
    # Prefer a human caption file over an auto-generated one (auto files contain ".auto").
    human = [p for p in srts if ".auto." not in p.name]
    return human[0] if human else srts[0]


def srt_to_text(srt_path: Path) -> str:
    text_lines: list[str] = []
    for raw in srt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.isdigit() or "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line)  # strip inline VTT/SRT tags
        if line:
            text_lines.append(line)
    # Auto-captions repeat lines as they scroll — collapse consecutive duplicates.
    deduped: list[str] = []
    for line in text_lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped)


def download_audio_only(url: str, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    template = str(out / "yt_audio.%(ext)s")
    run(ytdlp_cmd() + ["-f", "bestaudio", "-x", "--audio-format", "wav", "-o", template, url])
    candidates = sorted(out.glob("yt_audio.*"))
    require(bool(candidates), "yt-dlp did not produce an audio file.")
    return candidates[0]


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def cmd_check(_args: argparse.Namespace) -> int:
    print(json.dumps(environment_report(), ensure_ascii=False, indent=2))
    return 0


def cmd_install(_args: argparse.Namespace) -> int:
    run([sys.executable, "-m", "pip", "install", "-U", "openai-whisper", "yt-dlp"])
    print(json.dumps(environment_report(), ensure_ascii=False, indent=2))
    return 0


def cmd_media(args: argparse.Namespace) -> int:
    src = Path(args.source).expanduser()
    require(src.exists(), f"file not found: {src}")
    out = Path(args.out).expanduser()
    gpu = detect_gpu()
    device = resolve_device(args.device, gpu)

    suffix = src.suffix.lower()
    if suffix in AUDIO_SUFFIXES or suffix in VIDEO_SUFFIXES:
        audio = extract_audio_16k_mono(src, out)
    else:
        # Unknown container — let ffmpeg try anyway; whisper also resamples internally.
        audio = extract_audio_16k_mono(src, out)

    result = transcribe_with_whisper(audio, model_name=args.model, device=device, language=args.language)
    segments = [
        {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
        for seg in result.get("segments", [])
    ]
    write_outputs(
        out,
        text=result.get("text", ""),
        segments=segments,
        srt=segments_to_srt(segments) if segments else None,
        meta={
            "source": str(src),
            "kind": "media",
            "model": args.model,
            "device": device,
            "language": result.get("language", args.language),
            "gpu": gpu,
        },
    )
    print(json.dumps({"out": str(out), "device": device, "segments": len(segments)}, ensure_ascii=False, indent=2))
    return 0


def cmd_url(args: argparse.Namespace) -> int:
    out = Path(args.out).expanduser()
    srt = fetch_captions(args.source, out, args.lang)
    if srt is not None:
        text = srt_to_text(srt)
        # Re-stamp the canonical output names from the chosen caption file.
        (out / "transcript.srt").write_text(srt.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        write_outputs(
            out,
            text=text,
            segments=None,
            srt=None,  # already written from the caption file above
            meta={"source": args.source, "kind": "url", "path": "captions", "caption_file": srt.name},
        )
        print(json.dumps({"out": str(out), "path": "captions", "caption_file": srt.name}, ensure_ascii=False, indent=2))
        return 0

    # No captions — fall back to audio-only download + whisper.
    print("no captions found; falling back to audio-only download + whisper", file=sys.stderr)
    gpu = detect_gpu()
    device = resolve_device(args.device, gpu)
    audio = download_audio_only(args.source, out)
    result = transcribe_with_whisper(audio, model_name=args.model, device=device, language=args.language)
    segments = [
        {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
        for seg in result.get("segments", [])
    ]
    write_outputs(
        out,
        text=result.get("text", ""),
        segments=segments,
        srt=segments_to_srt(segments) if segments else None,
        meta={
            "source": args.source,
            "kind": "url",
            "path": "whisper",
            "model": args.model,
            "device": device,
            "language": result.get("language", args.language),
            "gpu": gpu,
        },
    )
    print(json.dumps({"out": str(out), "path": "whisper", "device": device, "segments": len(segments)}, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Report dependency and GPU availability.").set_defaults(func=cmd_check)
    sub.add_parser("install", help="pip install -U openai-whisper yt-dlp.").set_defaults(func=cmd_install)

    common_out = {"default": "./transcript_out", "help": "Output directory (default ./transcript_out)."}

    p_media = sub.add_parser("media", help="Transcribe a local media file.")
    p_media.add_argument("source", help="Path to a local audio/video file.")
    p_media.add_argument("--model", default="small", help="whisper model size (default small).")
    p_media.add_argument("--language", default=None, help="Force language code (e.g. en, zh). Default: auto-detect.")
    p_media.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    p_media.add_argument("--out", **common_out)
    p_media.set_defaults(func=cmd_media)

    p_url = sub.add_parser("url", help="Fetch captions via yt-dlp; fall back to whisper.")
    p_url.add_argument("source", help="Online video URL (YouTube, etc.).")
    p_url.add_argument("--lang", default="en.*,zh.*,zh-Hans,zh-CN", help="yt-dlp --sub-langs filter for captions.")
    p_url.add_argument("--model", default="small", help="whisper model for the no-caption fallback.")
    p_url.add_argument("--language", default=None, help="Force language for the whisper fallback.")
    p_url.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    p_url.add_argument("--out", **common_out)
    p_url.set_defaults(func=cmd_url)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
