---
name: notetaker
description: >
  Use when a user wants notes written from source material — a local video/audio file, an
  online video URL (YouTube, etc.), a PDF (papers, books, slides, reports), or text the user
  supplies. Stage 1 ingests the source into clean text or structured content: openai-whisper
  + FFmpeg for media (GPU-accelerated only when a CUDA device is present), yt-dlp for online
  videos (grabs captions without downloading the video), and MinerU / Docling / PyMuPDF4LLM /
  PyMuPDF for PDFs by document type. Stage 2 (note synthesis) is added in a later section. An
  optional Stage 3 renders visualizations (Matplotlib charts, Graphviz / Mermaid diagrams,
  LaTeX formulas) to embed into the notes. Triggers on phrases like "take/make notes from this
  video/lecture/PDF", "transcribe this and summarize", "turn this into study notes",
  "把这个视频/讲座/PDF 整理成笔记", "帮我做笔记".
---

# Learn Video Course

Turn course material into study notes:

1. **Ingest** the source into clean text or structured content.
2. **Synthesize** Markdown notes from that content.
3. **Visualize** *(optional)* — render figures, diagrams, and formulas to embed in the notes.

> Build status: this file implements Stage 1 ingestion for video / audio / online-video
> sources (Stage 1a) and PDF (Stage 1b), and Stage 3 visualization (`scripts/render_visual.py`).
> Note synthesis is filled in as a separate section.

## Prerequisites & install

The scripts shell out to `python3` and `pip`, plus the per-stage tools below. Run each
stage's `check` subcommand first to see what's missing, and **ask the user before installing**
anything — several deps are large (whisper pulls in `torch`; MinerU and Docling download
models on first run).

- **Python 3 + pip** must already be on PATH. **MinerU additionally requires Python 3.10–3.13.**
- **FFmpeg** is a system package (not pip) — install commands are in Stage 1a.
- **Stage 3 visualization** adds light pip deps (`matplotlib`, `numpy`, `graphviz` — no model
  downloads) and two *optional* system tools: the Graphviz `dot` binary and the Mermaid CLI
  (`mmdc`, via npm). See Stage 3.
- **Recommended: install into an isolated venv** so the heavy deps (`torch`, `docling`,
  `mineru`) don't pollute system Python. Run every `python3` / `pip` command below from inside it:

  ```bash
  python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
  ```

Per-tool install commands live in each stage's "Installing…" subsection. Both scripts also
expose a `check` subcommand (probe what's available) and an `install` subcommand (pip-install
for you).

## Routing — pick the ingestion path

| Source the user gives | Path |
|---|---|
| Local video or audio file (`.mp4 .mkv .mov .webm .mp3 .m4a .wav .flac` …) | Stage 1a — extract audio with FFmpeg, transcribe with openai-whisper |
| Online video URL (YouTube and other yt-dlp sites) | Stage 1a — yt-dlp fetches captions **without downloading the video**; only if no captions exist, download audio-only and transcribe |
| PDF | Stage 1b — inspect the document, route to MinerU / Docling / PyMuPDF4LLM / PyMuPDF |

After Stage 1 produces a transcript/structured text, continue to Stage 2 note synthesis
*(added in a later step)*.

## Stage 1a — Video / Audio → transcript

All work goes through `scripts/extract_transcript.py`. It handles dependency checks, GPU
detection, FFmpeg audio extraction, and whisper transcription, and writes its outputs into
an `--out` directory (default `./transcript_out`):

- `transcript.txt` — plain-text transcript
- `transcript.srt` — timestamped subtitles (when segment timing is available)
- `segments.json` — structured `{start, end, text}` segments (whisper path only)
- `meta.json` — run metadata (source, model, device, language)

### Step 0 — Check the environment first

```bash
python3 scripts/extract_transcript.py check
```

This prints JSON reporting whether `ffmpeg`, `openai-whisper` (and `torch`), and `yt-dlp`
are installed, and whether a CUDA GPU (or Apple MPS) is available. **Always run this before
transcribing** so you know which dependencies to install and whether GPU acceleration is on
the table.

### Installing missing dependencies (ask the user first)

Only install after telling the user what you'll run and getting an OK.

- **openai-whisper** (pulls in `torch`): `pip install -U openai-whisper`
- **yt-dlp**: `pip install -U yt-dlp`
- Both Python deps at once: `python3 scripts/extract_transcript.py install`
- **FFmpeg** (system package, not pip):
  - macOS: `brew install ffmpeg`
  - Debian/Ubuntu: `sudo apt-get install -y ffmpeg`
  - Windows: `choco install ffmpeg` (or `winget install Gyan.FFmpeg`)

### GPU acceleration policy

The script auto-detects the device and **only enables GPU when it actually helps**:

- **CUDA GPU present** → transcribe on `cuda` with `fp16`. Safe to use a larger model
  (`medium` / `large-v3`).
- **No CUDA** → run on CPU. Prefer a smaller model (`base` or `small`) so CPU runs stay
  fast. This is the normal case on macOS.
- **Apple Silicon (MPS)** → whisper's MPS path is unreliable for some ops, so the script
  stays on CPU by default. Only pass `--device mps` if the user explicitly wants to try it.

Override detection with `--device {auto,cpu,cuda,mps}` when needed; default is `auto`.

### Transcribe a local media file

```bash
python3 scripts/extract_transcript.py media <path-to-file> \
  --model small --out ./transcript_out
# add --language zh  (or en, ...) to skip language auto-detection and speed things up
```

FFmpeg first downmixes to 16 kHz mono WAV, then whisper transcribes it.

### Transcribe an online video (captions-first)

```bash
python3 scripts/extract_transcript.py url "<video-url>" \
  --lang "en.*,zh.*,zh-Hans,zh-CN" --out ./transcript_out
```

The script tries human + auto captions via yt-dlp first (no video download). If the video
has no captions in the requested languages, it downloads **audio only** and falls back to
whisper — add `--model small` to control that fallback.

### Picking a whisper model

`tiny` < `base` < `small` < `medium` < `large-v3` — bigger is more accurate but slower and
heavier on memory. Default `small`. On CPU, don't go above `small` unless the user accepts a
long run; on a CUDA GPU, `medium`/`large-v3` are reasonable.

## Stage 1b — PDF → structured content

All work goes through `scripts/extract_pdf.py`. It picks the extractor that fits the
document, runs it, and writes outputs into an `--out` directory (default `./pdf_out`):
`content.md` (or `content.txt` for the raw PyMuPDF path), an `images/` folder, `blocks.json`
/ `document.json` when the tool provides structure, and `meta.json`.

### The four extractors and when each wins

| Tool | Best for | Output |
|---|---|---|
| **MinerU** | Chinese papers, double-column papers, formulas, complex tables, **scanned** PDFs (OCR) | Markdown + images + layout JSON |
| **Docling** | Contracts, reports, books, RAG prep — structured content with images & tables | Markdown + `document.json` |
| **PyMuPDF4LLM** | Large, text-heavy PDFs that just need fast lightweight Markdown | Markdown + images |
| **PyMuPDF** (`fitz`) | You only want raw text + coordinates + embedded images, nothing inferred | `content.txt` + `blocks.json` + images |

### Step 0 — Inspect first, then route

```bash
python3 scripts/extract_pdf.py inspect <pdf>
```

`inspect` uses only PyMuPDF (lightweight) to report signals — page count, CJK ratio,
two-column layout, formula density, images per page, whether the PDF is scanned — and prints
a `recommended_tool`. Use it to decide, then confirm against what the user told you (e.g. if
they say "this is a paper with lots of formulas", prefer **MinerU** even if signals are
borderline).

Routing logic the script applies:

- **scanned** (little/no extractable text) → MinerU if CJK, else Docling (both OCR)
- **double-column or formula-heavy** → MinerU (covers English papers too)
- **CJK-heavy** prose → MinerU
- **image/table-rich** structured doc → Docling
- **large, text-heavy, few images** → PyMuPDF4LLM
- otherwise → Docling

### Run extraction

```bash
# Let the script inspect + pick:
python3 scripts/extract_pdf.py extract <pdf> --tool auto --out ./pdf_out
# Or force a specific tool when you know better:
python3 scripts/extract_pdf.py extract <pdf> --tool mineru --out ./pdf_out
```

`--tool auto` runs `inspect`, picks a tool, and — if that tool isn't installed — **stops with
the install command instead of downloading models**. MinerU and Docling are heavy (model
downloads); always confirm with the user before installing.

### Installing missing extractors (ask the user first)

- **PyMuPDF** (needed for `inspect` and the raw path): `pip install -U pymupdf`
- **PyMuPDF4LLM**: `pip install -U pymupdf4llm`
- **Docling**: `pip install -U docling`
- **MinerU**: `pip install -U "mineru[core]"` — lighter, works CPU/MPS. Use `"mineru[all]"`
  on a CUDA server for the VLM backends. Or via the script: `python3
  scripts/extract_pdf.py install --tool mineru`.

### GPU / model-source notes for MinerU

- MinerU's `pipeline` backend (the script's default `--backend pipeline`) runs on **CPU and
  Apple MPS** — unlike whisper, MPS is fine here. A CUDA GPU is faster still.
- First run downloads models from HuggingFace. If the network blocks HF (common in mainland
  China), set `MINERU_MODEL_SOURCE=modelscope` in the environment before running.

## Stage 3 — Visualization (optional enrichment)

When the notes would benefit from a picture — a formula, an algorithm / data-structure
diagram, or a data chart — use `scripts/render_visual.py`. Each render writes an artifact into
`--out` (default `./viz_out`) and prints a JSON result whose `markdown` field is a
**paste-ready snippet** to drop straight into the notes.

### Match the tool to the content

| Content | Tool | How it lands in the notes |
|---|---|---|
| **Math formula** | inline `$$ … $$` (no tool); `formula` only for a standalone image | the viewer's MathJax/KaTeX renders `$$…$$`; zero deps |
| **Data / function plot / chart** | `mpl` (Matplotlib) | `![](figure.svg)` image link |
| **Algorithm / tree / graph / state machine / flow** | `dot` (Graphviz) **or** `mermaid` | Graphviz → `![](graph.svg)` image; Mermaid → a ` ```mermaid ` text block |

Two rules of thumb:

- **Formulas — don't rasterize by default.** Emit `$$ … $$` straight into the Markdown;
  Obsidian, GitHub, and most viewers render it. Reach for `formula` only when you need an
  actual image file (e.g. a viewer with no math support).
- **Diagrams — pick by where the notes are read.** Prefer **Mermaid embed** for Obsidian /
  GitHub / VS Code (the diagram stays as diffable text, no image files to manage); prefer
  **Graphviz SVG** when you need a portable image or richer automatic graph layout.

### Step 0 — Check the environment first

```bash
python3 scripts/render_visual.py check
```

Reports whether `matplotlib`, `numpy`, the Python `graphviz` binding, the Graphviz `dot`
binary, the Mermaid CLI (`mmdc`), Node, and LaTeX are present.

### Installing (ask the user first)

The Python deps are light — no model downloads:

```bash
python3 scripts/render_visual.py install     # pip install -U matplotlib numpy graphviz
```

The two non-pip tools are installed separately, only when you actually need them:

- **Graphviz `dot`** (for `dot` rendering): macOS `brew install graphviz`; Debian/Ubuntu
  `sudo apt-get install -y graphviz`; Windows `choco install graphviz`.
- **Mermaid CLI** (only for `mermaid --mode render`): `npm install -g @mermaid-js/mermaid-cli`.
  Not needed for the default embed mode.

### Data & function plots — `mpl`

You write the Matplotlib code; the script runs it headlessly and saves the current figure.
`plt` (pyplot), `np` (numpy), and `math` are pre-imported — the snippet just draws.

```bash
echo 'plt.plot([0,1,2,3],[0,1,4,9],marker="o"); plt.title(r"$y = x^2$"); plt.grid(True)' \
  | python3 scripts/render_visual.py mpl - --name squares --out ./viz_out
# or pass a file:  python3 scripts/render_visual.py mpl plot.py --name fig1
```

Use mathtext (`r"$y = x^2$"`) for math in titles/labels — it renders a real superscript on any
font. A raw `²` may warn "glyph missing" when the chosen CJK font lacks that exact character.

Output `markdown` is `![squares](squares.svg)` (path is relative to `--out` — prepend your
notes' image folder if needed). SVG is the default; use `--format png` (or `pdf`) for a raster.
Chinese titles/labels work when a CJK font is installed (the script auto-selects one).

### Algorithm / structure diagrams — `dot` (Graphviz)

```bash
printf 'digraph { rankdir=LR; A -> B -> C; B -> D }' \
  | python3 scripts/render_visual.py dot - --name pipeline
```

### Algorithm / flow diagrams — `mermaid`

Default **embed** mode needs no tools and returns a fenced block to paste in:

```bash
printf 'flowchart TD\n  Start --> Check{ok?}\n  Check -->|yes| Done\n  Check -->|no| Start' \
  | python3 scripts/render_visual.py mermaid - --name flow
# --mode render writes an SVG via mmdc instead (needs the Mermaid CLI)
```

### Standalone formula image — `formula`

Only when you need an image rather than inline `$$…$$`:

```bash
python3 scripts/render_visual.py formula "e^{i\pi} + 1 = 0" --name euler
# --usetex uses a real LaTeX install (if present); default is Matplotlib mathtext (no LaTeX)
```

### Note on `mpl` and trust

`mpl` executes the Matplotlib code you hand it (headless `Agg` backend) — the same trust level
as any other command the skill runs locally. Keep the snippets to plotting.
