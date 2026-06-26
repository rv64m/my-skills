#!/usr/bin/env python3
"""Extract structured content from a PDF, routing to the right tool for the document.

Tool selection (the user's policy)
----------------------------------
  mineru        Chinese / double-column papers, formulas, complex tables, scanned PDFs.
  docling       Contracts, reports, books, RAG prep — structured content + images + tables.
  pymupdf4llm   Large text-heavy PDFs that just need fast, lightweight Markdown.
  pymupdf       Raw text + coordinates + embedded images, nothing fancy.

Subcommands
-----------
  check                       Report which extractors (and GPU) are available.
  inspect  <pdf>              Analyse the PDF with PyMuPDF and recommend a tool (no heavy deps).
  extract  <pdf> --tool ...   Run an extractor. --tool auto runs inspect first and picks.
  install  --tool <name>      pip install -U the chosen extractor.

`inspect` only needs PyMuPDF (lightweight). The heavy tools (mineru, docling) are never
auto-installed: `extract --tool auto` recommends one and, if it is missing, prints the
install command and stops so you can confirm before downloading models.

Outputs land in --out (default ./pdf_out): content.md (or content.txt for pymupdf),
plus images/, blocks.json / document.json where the tool provides them, and meta.json.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = ["mineru", "docling", "pymupdf4llm", "pymupdf"]

INSTALL = {
    "mineru": [sys.executable, "-m", "pip", "install", "-U", "mineru[core]"],
    "docling": [sys.executable, "-m", "pip", "install", "-U", "docling"],
    "pymupdf4llm": [sys.executable, "-m", "pip", "install", "-U", "pymupdf4llm"],
    "pymupdf": [sys.executable, "-m", "pip", "install", "-U", "pymupdf"],
}

# Unicode ranges used by the lightweight inspector.
CJK_RANGES = [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF)]
MATH_RANGES = [
    (0x2200, 0x22FF),  # mathematical operators
    (0x2A00, 0x2AFF),  # supplemental math operators
    (0x27C0, 0x27EF),  # misc math symbols-A
    (0x2980, 0x29FF),  # misc math symbols-B
    (0x0370, 0x03FF),  # Greek (variables in formulas)
    (0x2100, 0x214F),  # letterlike symbols
    (0x2070, 0x209F),  # super/subscripts
]


# --------------------------------------------------------------------------- #
# Environment probing
# --------------------------------------------------------------------------- #
def have_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def import_fitz():
    """PyMuPDF imports as `fitz` (and as `pymupdf` on newer builds)."""
    try:
        import fitz  # type: ignore

        return fitz
    except Exception:
        try:
            import pymupdf as fitz  # type: ignore

            return fitz
        except Exception as exc:
            raise SystemExit(f"PyMuPDF is required for inspection: {' '.join(INSTALL['pymupdf'])} ({exc})")


def detect_gpu() -> dict:
    info = {"cuda": False, "cuda_name": None, "mps": False, "nvidia_smi": have_cmd("nvidia-smi")}
    if module_available("torch"):
        try:
            import torch  # local import: heavy, optional

            info["cuda"] = bool(torch.cuda.is_available())
            if info["cuda"]:
                info["cuda_name"] = torch.cuda.get_device_name(0)
            info["mps"] = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        except Exception as exc:
            info["torch_error"] = str(exc)
    return info


def tool_available(name: str) -> bool:
    if name == "mineru":
        return have_cmd("mineru") or module_available("mineru")
    if name == "pymupdf":
        return module_available("fitz") or module_available("pymupdf")
    return module_available(name)


def environment_report() -> dict:
    return {tool: tool_available(tool) for tool in TOOLS} | {"gpu": detect_gpu()}


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def run(cmd: list[str], *, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, check=check, env=env)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def in_ranges(code: int, ranges: list[tuple[int, int]]) -> bool:
    return any(low <= code <= high for low, high in ranges)


# --------------------------------------------------------------------------- #
# Lightweight inspection (PyMuPDF) → routing recommendation
# --------------------------------------------------------------------------- #
def looks_two_column(blocks: list, width: float) -> bool:
    if width <= 0:
        return False
    text_blocks = [b for b in blocks if len(b) >= 7 and b[6] == 0 and str(b[4]).strip()]
    if len(text_blocks) < 4:
        return False
    left = right = straddle = 0
    mid_left, mid_right = width * 0.45, width * 0.55
    for x0, y0, x1, y1, *_ in text_blocks:
        if x1 <= mid_right and x0 < width * 0.5:
            left += 1
        elif x0 >= mid_left and x1 > width * 0.5:
            right += 1
        if x0 < width * 0.40 and x1 > width * 0.60:
            straddle += 1
    return left >= 2 and right >= 2 and straddle <= max(1, (left + right) // 6)


def inspect_pdf(path: Path) -> dict:
    fitz = import_fitz()
    doc = fitz.open(str(path))
    page_count = doc.page_count
    require(page_count > 0, "PDF has no pages.")

    sample = min(page_count, 10)
    indices = sorted({int(round(i * (page_count - 1) / max(sample - 1, 1))) for i in range(sample)})

    total_chars = cjk_chars = math_chars = image_count = two_col_votes = pages_with_text = 0
    for idx in indices:
        page = doc[idx]
        text = page.get_text("text")
        if text.strip():
            pages_with_text += 1
        total_chars += len(text)
        for ch in text:
            code = ord(ch)
            if in_ranges(code, CJK_RANGES):
                cjk_chars += 1
            elif in_ranges(code, MATH_RANGES):
                math_chars += 1
        image_count += len(page.get_images(full=True))
        if looks_two_column(page.get_text("blocks"), page.rect.width):
            two_col_votes += 1

    sampled = len(indices)
    chars_per_page = total_chars / sampled
    sig = {
        "pages": page_count,
        "sampled_pages": sampled,
        "scanned": pages_with_text == 0 or chars_per_page < 50,
        "cjk_ratio": round(cjk_chars / max(total_chars, 1), 3),
        "math_per_page": round(math_chars / sampled, 1),
        "likely_formulas": (math_chars / sampled) >= 12,
        "images_per_page": round(image_count / sampled, 2),
        "two_column": two_col_votes >= math.ceil(sampled / 2),
        "chars_per_page": round(chars_per_page, 0),
    }
    tool, why = recommend(sig)
    sig["recommended_tool"] = tool
    sig["reason"] = why
    return sig


def recommend(sig: dict) -> tuple[str, str]:
    if sig["scanned"]:
        if sig["cjk_ratio"] >= 0.15:
            return "mineru", "scanned/image PDF with CJK text → MinerU OCR + layout"
        return "docling", "scanned/image PDF → Docling OCR pipeline"
    if sig["two_column"] or sig["likely_formulas"]:
        lang = "CJK " if sig["cjk_ratio"] >= 0.15 else ""
        return "mineru", f"{lang}double-column / formula-heavy layout → MinerU"
    if sig["cjk_ratio"] >= 0.30:
        return "mineru", "CJK-heavy document → MinerU"
    if sig["images_per_page"] >= 0.5:
        return "docling", "image/table-rich structured document → Docling"
    if sig["pages"] >= 20 and sig["images_per_page"] < 0.2:
        return "pymupdf4llm", "large text-heavy PDF → PyMuPDF4LLM (lightweight, fast)"
    return "docling", "general structured extraction → Docling"


# --------------------------------------------------------------------------- #
# Extractors
# --------------------------------------------------------------------------- #
def extract_pymupdf(path: Path, out: Path) -> dict:
    fitz = import_fitz()
    out.mkdir(parents=True, exist_ok=True)
    images_dir = out / "images"
    images_dir.mkdir(exist_ok=True)
    doc = fitz.open(str(path))

    text_parts: list[str] = []
    pages: list[dict] = []
    seen_xrefs: set[int] = set()
    for i, page in enumerate(doc):
        text_parts.append(f"\n\n----- page {i + 1} -----\n\n{page.get_text('text')}")
        blocks = []
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, btext, bno, btype = b[:7]
            blocks.append({"bbox": [x0, y0, x1, y1], "type": btype, "text": btext})
        pages.append({"page": i + 1, "width": page.rect.width, "height": page.rect.height, "blocks": blocks})
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            base = doc.extract_image(xref)
            (images_dir / f"img_x{xref}.{base['ext']}").write_bytes(base["image"])

    (out / "content.txt").write_text("".join(text_parts).strip() + "\n", encoding="utf-8")
    (out / "blocks.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"text_chars": sum(len(p) for p in text_parts), "images": len(seen_xrefs)}


def extract_pymupdf4llm(path: Path, out: Path) -> dict:
    require(module_available("pymupdf4llm"), f"not installed: {' '.join(INSTALL['pymupdf4llm'])}")
    import pymupdf4llm  # local import

    out.mkdir(parents=True, exist_ok=True)
    images_dir = out / "images"
    images_dir.mkdir(exist_ok=True)
    md = pymupdf4llm.to_markdown(
        str(path),
        write_images=True,
        image_path=str(images_dir),
        image_format="png",
        dpi=150,
    )
    (out / "content.md").write_text(md, encoding="utf-8")
    return {"markdown_chars": len(md)}


def extract_docling(path: Path, out: Path) -> dict:
    require(module_available("docling"), f"not installed: {' '.join(INSTALL['docling'])}")
    from docling.document_converter import DocumentConverter  # local import

    out.mkdir(parents=True, exist_ok=True)
    result = DocumentConverter().convert(str(path))
    md = result.document.export_to_markdown()
    (out / "content.md").write_text(md, encoding="utf-8")
    try:
        (out / "document.json").write_text(
            json.dumps(result.document.export_to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:  # export_to_dict is version-sensitive; markdown is the contract
        print(f"warning: docling export_to_dict failed: {exc}", file=sys.stderr)
    return {"markdown_chars": len(md)}


def extract_mineru(path: Path, out: Path, backend: str) -> dict:
    require(tool_available("mineru"), f"not installed: {' '.join(INSTALL['mineru'])}")
    out.mkdir(parents=True, exist_ok=True)
    base = ["mineru"] if have_cmd("mineru") else [sys.executable, "-m", "mineru"]
    cmd = base + ["-p", str(path), "-o", str(out)]
    if backend:
        cmd += ["-b", backend]
    run(cmd)
    produced = [str(p.relative_to(out)) for p in sorted(out.rglob("*.md"))]
    return {"markdown_files": produced}


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def cmd_check(_args: argparse.Namespace) -> int:
    print(json.dumps(environment_report(), ensure_ascii=False, indent=2))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    path = Path(args.source).expanduser()
    require(path.exists(), f"file not found: {path}")
    print(json.dumps(inspect_pdf(path), ensure_ascii=False, indent=2))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    require(args.tool in INSTALL, f"unknown tool: {args.tool}")
    run(INSTALL[args.tool])
    print(json.dumps(environment_report(), ensure_ascii=False, indent=2))
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    path = Path(args.source).expanduser()
    require(path.exists(), f"file not found: {path}")
    out = Path(args.out).expanduser()

    tool = args.tool
    signals = None
    if tool == "auto":
        signals = inspect_pdf(path)
        tool = signals["recommended_tool"]
        print(f"auto-selected '{tool}': {signals['reason']}", file=sys.stderr)

    if not tool_available(tool):
        raise SystemExit(
            f"'{tool}' is not installed. Install it with:\n  {' '.join(INSTALL[tool])}\n"
            f"then re-run. (Heavy tools are not auto-installed — confirm with the user first.)"
        )

    if tool == "pymupdf":
        stats = extract_pymupdf(path, out)
    elif tool == "pymupdf4llm":
        stats = extract_pymupdf4llm(path, out)
    elif tool == "docling":
        stats = extract_docling(path, out)
    elif tool == "mineru":
        stats = extract_mineru(path, out, args.backend)
    else:
        raise SystemExit(f"unknown tool: {tool}")

    meta = {"source": str(path), "tool": tool, "out": str(out), "stats": stats}
    if signals is not None:
        meta["signals"] = signals
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "tool": tool, **stats}, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Report extractor and GPU availability.").set_defaults(func=cmd_check)

    p_inspect = sub.add_parser("inspect", help="Analyse a PDF and recommend a tool.")
    p_inspect.add_argument("source", help="Path to the PDF.")
    p_inspect.set_defaults(func=cmd_inspect)

    p_install = sub.add_parser("install", help="pip install -U an extractor.")
    p_install.add_argument("--tool", required=True, choices=TOOLS)
    p_install.set_defaults(func=cmd_install)

    p_extract = sub.add_parser("extract", help="Extract content from a PDF.")
    p_extract.add_argument("source", help="Path to the PDF.")
    p_extract.add_argument("--tool", default="auto", choices=["auto", *TOOLS])
    p_extract.add_argument("--out", default="./pdf_out", help="Output directory (default ./pdf_out).")
    p_extract.add_argument(
        "--backend",
        default="pipeline",
        help="MinerU backend (default 'pipeline' — works on CPU and Apple MPS). Set '' to use MinerU's default.",
    )
    p_extract.set_defaults(func=cmd_extract)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
