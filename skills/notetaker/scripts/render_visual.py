#!/usr/bin/env python3
"""Render visualizations to embed into the study notes (Stage 3, optional enrichment).

Each render writes an artifact into --out and prints a JSON result whose `markdown`
field is a paste-ready snippet for the notes (an `![](...)` image link, or a fenced
```mermaid block for Mermaid embed mode).

Subcommands
-----------
  check                     Report which renderers are available (matplotlib / numpy /
                            graphviz / dot / mermaid-cli / node / latex) plus optional
                            math helpers (scipy / sympy / pandas).
  install                   pip install -U the light Python deps (matplotlib numpy graphviz);
                            add --with-math or --optional for math helpers.
  mpl      <src.py|->       Run agent-written Matplotlib code; save the current figure.
  dot      <src.dot|->      Render Graphviz DOT (trees / graphs / state machines / flowcharts).
  mermaid  <src.mmd|->      Embed a Mermaid diagram as text (default) or render it via mmdc.
  formula  "<latex>"        Render a standalone LaTeX formula image (mathtext; no LaTeX needed).

Tool-vs-content guidance
------------------------
  formulas              Prefer inline `$$...$$` in the note (MathJax renders it, zero deps);
                        use `formula` only when you need a standalone image file.
  data / function plots Matplotlib (`mpl`).
  algorithms / structs  Graphviz (`dot`) for an image, or Mermaid (`mermaid`) to keep the
                        diagram as text inside the Markdown.

Outputs land in --out (default ./viz_out): <name>.<format> for image renderers, <name>.mmd
plus a fenced block for Mermaid embed mode.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

PIP_DEPS = ["matplotlib", "numpy", "graphviz"]
OPTIONAL_PIP_DEPS = {
    "scipy": "scipy",
    "sympy": "sympy",
    "pandas": "pandas",
}

# Non-pip tools: detected but never auto-installed — we print these hints instead.
SYSTEM_HINTS = {
    "graphviz_dot": (
        "system Graphviz (the `dot` binary): macOS `brew install graphviz`; "
        "Debian/Ubuntu `sudo apt-get install -y graphviz`; Windows `choco install graphviz`."
    ),
    "mermaid_cli": (
        "Mermaid CLI: `npm install -g @mermaid-js/mermaid-cli` (needs Node.js). "
        "Only needed for `mermaid --mode render`; embed mode needs nothing."
    ),
}

# Best-effort CJK fonts so Chinese titles/labels don't render as tofu boxes. First match wins.
CJK_FONT_CANDIDATES = [
    "PingFang SC", "Hiragino Sans GB", "Heiti SC", "Songti SC", "STHeiti", "Arial Unicode MS",
    "Noto Sans CJK SC", "Noto Sans CJK JP", "Source Han Sans SC", "WenQuanYi Zen Hei",
    "Microsoft YaHei", "SimHei",
]


# --------------------------------------------------------------------------- #
# Environment probing
# --------------------------------------------------------------------------- #
def have_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def try_import_module(name: str):
    """Import an optional module if it is fully usable, not just discoverable."""
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def environment_report() -> dict:
    return {
        "matplotlib": module_available("matplotlib"),
        "numpy": module_available("numpy"),
        "graphviz_py": module_available("graphviz"),
        "scipy": module_available("scipy"),
        "sympy": module_available("sympy"),
        "pandas": module_available("pandas"),
        "graphviz_dot": have_cmd("dot"),
        "mermaid_cli": have_cmd("mmdc"),
        "node": have_cmd("node"),
        "latex": have_cmd("latex") or have_cmd("pdflatex"),
    }


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, check=check)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def read_source(arg: str) -> str:
    """Read render source from a file path, or stdin when arg == '-'."""
    if arg == "-":
        return sys.stdin.read()
    path = Path(arg).expanduser()
    require(path.exists(), f"file not found: {path}")
    return path.read_text(encoding="utf-8")


def emit(out: Path, target: Path, fmt: str, *, markdown: str | None = None, extra: dict | None = None) -> int:
    """Print the canonical JSON result. `markdown` defaults to an image link by basename."""
    result = {
        "out": str(out),
        "file": str(target),
        "format": fmt,
        # Path is relative to --out; prepend your notes' image folder if needed.
        "markdown": markdown if markdown is not None else f"![{target.stem}]({target.name})",
    }
    if extra:
        result.update(extra)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Matplotlib helpers
# --------------------------------------------------------------------------- #
def configure_matplotlib(plt) -> None:
    """Neutral default style + CJK font + deterministic SVG hashing."""
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    cjk = [name for name in CJK_FONT_CANDIDATES if name in available]
    plt.rcParams.update(
        {
            "figure.figsize": (8, 5),
            "figure.dpi": 120,
            "savefig.dpi": 120,
            "font.size": 12,
            "axes.titlesize": 14,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.sans-serif": cjk + ["DejaVu Sans"],
            "axes.unicode_minus": False,  # render the minus sign even with a CJK font
            "svg.hashsalt": "learn-video-course",  # stable SVG element ids → clean git diffs
        }
    )


def savefig_kwargs(fmt: str) -> dict:
    # Strip the embedded date from SVGs so notes kept in git diff cleanly.
    return {"bbox_inches": "tight", "metadata": {"Date": None} if fmt == "svg" else None}


# --------------------------------------------------------------------------- #
# Graphviz
# --------------------------------------------------------------------------- #
def render_dot(src: str, target: Path, fmt: str) -> None:
    # The `dot` binary is the real requirement; the Python `graphviz` package is a convenience.
    require(
        have_cmd("dot"),
        "Graphviz `dot` binary not found — " + SYSTEM_HINTS["graphviz_dot"],
    )
    if module_available("graphviz"):
        import graphviz  # local import: optional dependency

        target.write_bytes(graphviz.Source(src).pipe(format=fmt))
        return
    proc = subprocess.run(
        ["dot", f"-T{fmt}"], input=src.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    require(proc.returncode == 0, f"dot failed: {proc.stderr.decode('utf-8', 'ignore').strip()}")
    target.write_bytes(proc.stdout)


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def cmd_check(_args: argparse.Namespace) -> int:
    print(json.dumps(environment_report(), ensure_ascii=False, indent=2))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    deps = [*PIP_DEPS]
    selected_optional = set(args.optional or [])
    if args.with_math:
        selected_optional.update(OPTIONAL_PIP_DEPS)
    deps.extend(OPTIONAL_PIP_DEPS[name] for name in sorted(selected_optional))

    run([sys.executable, "-m", "pip", "install", "-U", *deps])
    report = environment_report()
    for key, hint in SYSTEM_HINTS.items():
        if not report[key]:
            print(f"note: {key} still unavailable — {hint}", file=sys.stderr)
    missing_optional = [name for name in OPTIONAL_PIP_DEPS if not report[name]]
    if missing_optional:
        print(
            "note: optional math helpers unavailable — "
            + ", ".join(missing_optional)
            + ". Install selected helpers with `python3 scripts/render_visual.py install --optional "
            + " ".join(missing_optional)
            + "` or all of them with `--with-math`.",
            file=sys.stderr,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def preload_scientific_namespace(namespace: dict) -> list[str]:
    """Expose installed scientific helpers to mpl snippets without making them required."""
    preloaded = sorted(namespace)

    scipy_mod = try_import_module("scipy")
    if scipy_mod is not None:
        namespace["scipy"] = scipy_mod
        preloaded.append("scipy")
        for submodule in ("stats", "optimize", "linalg", "special"):
            module = try_import_module(f"scipy.{submodule}")
            if module is not None:
                namespace[submodule] = module
                preloaded.append(submodule)

    sympy_mod = try_import_module("sympy")
    if sympy_mod is not None:
        namespace["sympy"] = sympy_mod
        namespace["sy"] = sympy_mod
        preloaded.extend(["sympy", "sy"])

    pandas_mod = try_import_module("pandas")
    if pandas_mod is not None:
        namespace["pandas"] = pandas_mod
        namespace["pd"] = pandas_mod
        preloaded.extend(["pandas", "pd"])

    return sorted(set(preloaded))


def cmd_mpl(args: argparse.Namespace) -> int:
    require(
        module_available("matplotlib"),
        "matplotlib not installed — run: python3 scripts/render_visual.py install",
    )
    src = read_source(args.source)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{args.name}.{args.format}"

    import matplotlib

    matplotlib.use("Agg")  # headless: no display needed
    import matplotlib.pyplot as plt

    configure_matplotlib(plt)

    # Contract: the snippet draws using preloaded scientific helpers; we save the current figure.
    namespace: dict = {"plt": plt, "math": __import__("math")}
    if module_available("numpy"):
        import numpy as np

        namespace["np"] = np
        namespace["numpy"] = np
    preloaded = preload_scientific_namespace(namespace)
    try:
        exec(compile(src, "<mpl-snippet>", "exec"), namespace)
    except Exception as exc:  # surface a clean error, not a traceback dump
        require(False, f"matplotlib snippet failed: {type(exc).__name__}: {exc}")

    require(bool(plt.get_fignums()), "snippet produced no figure (did you call plt.plot/bar/...?).")
    plt.savefig(target, **savefig_kwargs(args.format))
    plt.close("all")
    return emit(out, target, args.format, extra={"preloaded": preloaded})


def cmd_dot(args: argparse.Namespace) -> int:
    src = read_source(args.source)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{args.name}.{args.format}"
    render_dot(src, target, args.format)
    return emit(out, target, args.format)


def cmd_mermaid(args: argparse.Namespace) -> int:
    src = read_source(args.source).strip()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    mmd_path = out / f"{args.name}.mmd"
    mmd_path.write_text(src + "\n", encoding="utf-8")

    if args.mode == "embed":
        block = "```mermaid\n" + src + "\n```"
        return emit(out, mmd_path, "mermaid", markdown=block)

    require(
        have_cmd("mmdc"),
        "Mermaid CLI `mmdc` not found — " + SYSTEM_HINTS["mermaid_cli"]
        + " Or use `--mode embed` to paste a ```mermaid block directly (no deps).",
    )
    target = out / f"{args.name}.{args.format}"
    run(["mmdc", "-i", str(mmd_path), "-o", str(target)])
    return emit(out, target, args.format)


def cmd_formula(args: argparse.Namespace) -> int:
    require(
        module_available("matplotlib"),
        "matplotlib not installed — run: python3 scripts/render_visual.py install",
    )
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{args.name}.{args.format}"

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    configure_matplotlib(plt)
    if args.usetex:
        require(
            have_cmd("latex") or have_cmd("pdflatex"),
            "--usetex needs a LaTeX install (TeX Live / MacTeX). Omit --usetex to use mathtext.",
        )
        plt.rcParams["text.usetex"] = True

    fig = plt.figure(figsize=(0.5, 0.5))
    fig.text(0.5, 0.5, f"${args.latex}$", ha="center", va="center", fontsize=args.fontsize)
    try:
        fig.savefig(target, pad_inches=0.1, transparent=True, **savefig_kwargs(args.format))
    except Exception as exc:
        plt.close(fig)
        require(False, f"formula render failed (check LaTeX/mathtext syntax): {exc}")
    plt.close(fig)
    return emit(
        out,
        target,
        args.format,
        extra={"hint": f"Most note viewers render inline `$${args.latex}$$` without an image."},
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def add_common(parser: argparse.ArgumentParser, default_name: str) -> None:
    parser.add_argument("--out", default="./viz_out", help="Output directory (default ./viz_out).")
    parser.add_argument("--name", default=default_name, help=f"Output file stem (default {default_name}).")
    parser.add_argument("--format", default="svg", choices=["svg", "png", "pdf"], help="Output format (default svg).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Report renderer availability.").set_defaults(func=cmd_check)
    p_install = sub.add_parser(
        "install",
        help="pip install -U matplotlib numpy graphviz; optionally scipy/sympy/pandas.",
    )
    p_install.add_argument(
        "--with-math",
        action="store_true",
        help="Also install optional math helpers: scipy sympy pandas.",
    )
    p_install.add_argument(
        "--optional",
        nargs="+",
        choices=sorted(OPTIONAL_PIP_DEPS),
        help="Install selected optional math helpers.",
    )
    p_install.set_defaults(func=cmd_install)

    p_mpl = sub.add_parser("mpl", help="Render agent-written Matplotlib code to an image.")
    p_mpl.add_argument("source", help="Path to a .py snippet, or '-' for stdin.")
    add_common(p_mpl, "figure")
    p_mpl.set_defaults(func=cmd_mpl)

    p_dot = sub.add_parser("dot", help="Render Graphviz DOT to an image.")
    p_dot.add_argument("source", help="Path to a .dot file, or '-' for stdin.")
    add_common(p_dot, "graph")
    p_dot.set_defaults(func=cmd_dot)

    p_mmd = sub.add_parser("mermaid", help="Embed a Mermaid diagram (text) or render it to an image.")
    p_mmd.add_argument("source", help="Path to a .mmd file, or '-' for stdin.")
    p_mmd.add_argument(
        "--mode",
        default="embed",
        choices=["embed", "render"],
        help="embed=fenced ```mermaid block (no deps, default); render=image via mmdc.",
    )
    add_common(p_mmd, "diagram")
    p_mmd.set_defaults(func=cmd_mermaid)

    p_f = sub.add_parser("formula", help="Render a LaTeX formula to a standalone image.")
    p_f.add_argument("latex", help="LaTeX math WITHOUT surrounding $, e.g. 'e^{i\\pi}+1=0'.")
    p_f.add_argument("--fontsize", type=int, default=28, help="Font size in points (default 28).")
    p_f.add_argument("--usetex", action="store_true", help="Use a real LaTeX install instead of mathtext.")
    add_common(p_f, "equation")
    p_f.set_defaults(func=cmd_formula)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
