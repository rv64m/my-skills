#!/usr/bin/env python3
"""Create a temporary Python workspace for research synthesis tasks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


DEFAULT_PACKAGES = [
    "beautifulsoup4",
    "jupyterlab",
    "lxml",
    "matplotlib",
    "nbclient",
    "nbformat",
    "networkx",
    "numpy",
    "pandas",
    "pdfplumber",
    "pymupdf",
    "pypdf",
    "python-docx",
    "requests",
    "scienceplots",
    "scikit-learn",
    "scipy",
    "seaborn",
    "statsmodels",
    "sympy",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an isolated research workspace with a requirements file."
    )
    parser.add_argument(
        "--name",
        default="research-synthesis",
        help="Workspace name prefix inside the temp directory.",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        help="Directory in which to create the workspace. Defaults to the system temp directory.",
    )
    parser.add_argument(
        "--create-venv",
        action="store_true",
        help="Create a local .venv using the current Python interpreter.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install generated requirements into the .venv. Implies --create-venv.",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="Additional pip package to append. May be passed multiple times.",
    )
    return parser


def unique_workspace(base_dir: Path, name: str) -> Path:
    safe_name = "".join(char if char.isalnum() or char in "-_" else "-" for char in name)
    return Path(tempfile.mkdtemp(prefix=f"{safe_name}-", dir=base_dir))


def write_requirements(workspace: Path, packages: list[str]) -> Path:
    requirements = workspace / "requirements.txt"
    requirements.write_text("\n".join(sorted(set(packages))) + "\n", encoding="utf-8")
    return requirements


def write_starter_notebook_hint(workspace: Path) -> Path:
    hint = workspace / "analysis_notes.md"
    hint.write_text(
        """# Research Analysis Notes

Use this workspace for extracted text, cleaned tables, generated figures, and scratch notebooks.

Suggested directories:

- `inputs/` for copied source files
- `outputs/` for extracted text, tables, and figures
- `notebooks/` for exploratory notebooks
""",
        encoding="utf-8",
    )
    return hint


def create_venv(workspace: Path) -> Path:
    venv_path = workspace / ".venv"
    venv.EnvBuilder(with_pip=True).create(venv_path)
    return venv_path


def pip_path(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "pip.exe"
    return venv_path / "bin" / "pip"


def main() -> int:
    args = build_parser().parse_args()
    base_dir = args.base_dir or Path(tempfile.gettempdir())
    base_dir.mkdir(parents=True, exist_ok=True)

    workspace = unique_workspace(base_dir, args.name)
    for child in ("inputs", "outputs", "notebooks"):
        (workspace / child).mkdir()

    requirements = write_requirements(workspace, DEFAULT_PACKAGES + list(args.extra))
    notes = write_starter_notebook_hint(workspace)

    venv_path = None
    if args.create_venv or args.install:
        venv_path = create_venv(workspace)

    if args.install:
        subprocess.run(
            [str(pip_path(venv_path)), "install", "-r", str(requirements)],
            check=True,
        )

    result = {
        "workspace": str(workspace),
        "requirements": str(requirements),
        "notes": str(notes),
        "venv": str(venv_path) if venv_path else None,
        "activate": (
            f"source {venv_path / 'bin' / 'activate'}"
            if venv_path and sys.platform != "win32"
            else None
        ),
        "install": (
            f"{pip_path(venv_path)} install -r {requirements}" if venv_path else None
        ),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
