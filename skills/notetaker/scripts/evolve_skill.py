#!/usr/bin/env python3
"""Track evidence-backed improvements to the notetaker skill and validate revisions.

This helper does not edit the skill by itself. The agent uses it to retain small,
sanitized observations across runs, review recurring gaps, and verify a revision
after applying it with normal file-editing tools.

Subcommands
-----------
  observe    Record a reusable gap without storing raw source material.
  review     Summarize improvement candidates and their current status.
  resolve    Mark a candidate as applied, deferred, or rejected.
  validate   Check SKILL.md, referenced scripts, Python syntax, and CLI help.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STORE = "./notetaker_evolution.jsonl"
TARGETS = ("task", "skill", "script", "reference")
RESOLUTIONS = ("applied", "deferred", "rejected")
MAX_FIELD_CHARS = 1000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def clean_field(name: str, value: str, *, required: bool = True) -> str:
    cleaned = " ".join(value.split())
    require(not required or bool(cleaned), f"{name} must not be empty")
    require(
        len(cleaned) <= MAX_FIELD_CHARS,
        f"{name} exceeds {MAX_FIELD_CHARS} characters; record an abstract, not raw material",
    )
    return cleaned


def candidate_id(target: str, gap: str) -> str:
    normalized = re.sub(r"\s+", " ", gap.strip().lower())
    digest = hashlib.sha256(f"{target}\n{normalized}".encode()).hexdigest()
    return digest[:12]


def append_event(store: Path, event: dict) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def load_events(store: Path) -> list[dict]:
    if not store.exists():
        return []
    events: list[dict] = []
    for line_number, raw in enumerate(store.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"error: invalid JSON at {store}:{line_number}: {exc}") from exc
        require(isinstance(event, dict), f"{store}:{line_number} must contain a JSON object")
        events.append(event)
    return events


def candidate_state(events: list[dict]) -> dict[str, dict]:
    candidates: dict[str, dict] = {}
    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        if event.get("event") == "observation":
            current = candidates.setdefault(
                event_id,
                {
                    "id": event_id,
                    "first_seen": event.get("timestamp"),
                    "occurrences": 0,
                },
            )
            current.update(
                {
                    "last_seen": event.get("timestamp"),
                    "target": event.get("target"),
                    "source_kind": event.get("source_kind"),
                    "need": event.get("need"),
                    "gap": event.get("gap"),
                    "evidence": event.get("evidence"),
                    "proposal": event.get("proposal"),
                    "acceptance": event.get("acceptance"),
                    "status": "open",
                    "resolution_note": None,
                    "files": [],
                }
            )
            current["occurrences"] += 1
        elif event.get("event") == "resolution" and event_id in candidates:
            candidates[event_id].update(
                {
                    "status": event.get("status"),
                    "resolved_at": event.get("timestamp"),
                    "resolution_note": event.get("note"),
                    "files": event.get("files", []),
                }
            )
    return candidates


def emit(payload: dict, *, exit_code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


def cmd_observe(args: argparse.Namespace) -> int:
    target = args.target
    gap = clean_field("gap", args.gap)
    event_id = candidate_id(target, gap)
    store = Path(args.store).expanduser()
    event = {
        "schema": 1,
        "event": "observation",
        "id": event_id,
        "timestamp": utc_now(),
        "target": target,
        "source_kind": clean_field("source-kind", args.source_kind),
        "need": clean_field("need", args.need),
        "gap": gap,
        "evidence": clean_field("evidence", args.evidence),
        "proposal": clean_field("proposal", args.proposal, required=False),
        "acceptance": clean_field("acceptance", args.acceptance, required=False),
    }
    append_event(store, event)
    current = candidate_state(load_events(store))[event_id]
    return emit({"store": str(store), "candidate": current})


def cmd_review(args: argparse.Namespace) -> int:
    store = Path(args.store).expanduser()
    candidates = list(candidate_state(load_events(store)).values())
    if args.status != "all":
        candidates = [candidate for candidate in candidates if candidate["status"] == args.status]
    candidates.sort(key=lambda item: (-item["occurrences"], item["last_seen"], item["id"]))
    return emit({"store": str(store), "count": len(candidates), "candidates": candidates})


def cmd_resolve(args: argparse.Namespace) -> int:
    store = Path(args.store).expanduser()
    candidates = candidate_state(load_events(store))
    require(args.id in candidates, f"unknown candidate id: {args.id}")
    event = {
        "schema": 1,
        "event": "resolution",
        "id": args.id,
        "timestamp": utc_now(),
        "status": args.status,
        "note": clean_field("note", args.note, required=False),
        "files": args.files or [],
    }
    append_event(store, event)
    return emit({"store": str(store), "candidate": candidate_state(load_events(store))[args.id]})


def validate_frontmatter(skill_file: Path) -> list[str]:
    errors: list[str] = []
    if not skill_file.exists():
        return [f"missing {skill_file}"]
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return [f"{skill_file} must start with YAML frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return [f"{skill_file} has unterminated YAML frontmatter"]
    keys = {
        match.group(1)
        for line in lines[1:end]
        if (match := re.match(r"^([A-Za-z][A-Za-z0-9_-]*):", line))
    }
    missing = {"name", "description"} - keys
    extra = keys - {"name", "description"}
    if missing:
        errors.append(f"{skill_file} frontmatter is missing: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{skill_file} frontmatter has unsupported keys: {', '.join(sorted(extra))}")
    return errors


def validate_skill_root(root: Path) -> dict:
    skill_file = root / "SKILL.md"
    scripts_dir = root / "scripts"
    errors = validate_frontmatter(skill_file)
    checks = {
        "skill_file": str(skill_file),
        "frontmatter": not errors,
        "python_syntax": [],
        "cli_help": [],
        "script_references": [],
    }

    scripts = sorted(scripts_dir.glob("*.py")) if scripts_dir.exists() else []
    for script in scripts:
        try:
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
            checks["python_syntax"].append({"file": str(script), "ok": True})
        except SyntaxError as exc:
            checks["python_syntax"].append({"file": str(script), "ok": False})
            errors.append(f"{script}:{exc.lineno}: {exc.msg}")

    if skill_file.exists():
        text = skill_file.read_text(encoding="utf-8")
        references = sorted(set(re.findall(r"`(scripts/[A-Za-z0-9_.-]+\.py)`", text)))
        for reference in references:
            exists = (root / reference).exists()
            checks["script_references"].append({"path": reference, "ok": exists})
            if not exists:
                errors.append(f"SKILL.md references missing file: {reference}")

    for script in scripts:
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            ok = result.returncode == 0
            checks["cli_help"].append({"file": str(script), "ok": ok})
            if not ok:
                detail = (result.stderr or result.stdout).strip().splitlines()
                errors.append(f"{script} --help failed: {detail[-1] if detail else result.returncode}")
        except subprocess.TimeoutExpired:
            checks["cli_help"].append({"file": str(script), "ok": False})
            errors.append(f"{script} --help timed out")

    checks["frontmatter"] = not validate_frontmatter(skill_file)
    return {"ok": not errors, "root": str(root), "checks": checks, "errors": errors}


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    report = validate_skill_root(root)
    return emit(report, exit_code=0 if report["ok"] else 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    observe = sub.add_parser("observe", help="Record one sanitized, reusable improvement candidate.")
    observe.add_argument("--store", default=DEFAULT_STORE, help=f"JSONL state file (default {DEFAULT_STORE}).")
    observe.add_argument("--target", required=True, choices=TARGETS)
    observe.add_argument("--source-kind", required=True, help="General source type; do not include a private path or URL.")
    observe.add_argument("--need", required=True, help="Short abstraction of the user's desired outcome.")
    observe.add_argument("--gap", required=True, help="Reusable capability gap, not a raw source excerpt.")
    observe.add_argument("--evidence", required=True, help="Observed failure, workaround, or repeated request.")
    observe.add_argument("--proposal", default="", help="Candidate general improvement.")
    observe.add_argument("--acceptance", default="", help="How to verify the improvement.")
    observe.set_defaults(func=cmd_observe)

    review = sub.add_parser("review", help="List candidates, recurring gaps first.")
    review.add_argument("--store", default=DEFAULT_STORE, help=f"JSONL state file (default {DEFAULT_STORE}).")
    review.add_argument("--status", default="open", choices=("all", "open", *RESOLUTIONS))
    review.set_defaults(func=cmd_review)

    resolve = sub.add_parser("resolve", help="Record the disposition of a candidate.")
    resolve.add_argument("id", help="Candidate id from observe/review.")
    resolve.add_argument("--store", default=DEFAULT_STORE, help=f"JSONL state file (default {DEFAULT_STORE}).")
    resolve.add_argument("--status", required=True, choices=RESOLUTIONS)
    resolve.add_argument("--note", default="", help="Short reason or validation result.")
    resolve.add_argument("--files", nargs="*", help="Skill-relative files changed when status=applied.")
    resolve.set_defaults(func=cmd_resolve)

    validate = sub.add_parser("validate", help="Validate a notetaker skill directory.")
    validate.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Skill directory (default: parent of this script's scripts directory).",
    )
    validate.set_defaults(func=cmd_validate)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
