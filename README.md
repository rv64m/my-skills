# My Skills

Local skill collection packaged as both a Codex plugin and a Claude Code plugin.

## Layout

```text
my-skills/
├── .codex-plugin/plugin.json
├── .claude-plugin/plugin.json
├── claude-marketplace/.claude-plugin/marketplace.json
├── claude-marketplace/plugins/my-skills -> ../..
├── skills/
│   └── <skill-name>/SKILL.md
└── assets/
```

Add each skill as `skills/<skill-name>/SKILL.md`. Keep reusable scripts, references, or assets inside that skill folder so installed plugins do not depend on files outside the plugin root.

## Add A Skill

Use lowercase hyphen-case names:

```bash
python3 /Users/a1/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  my-skill \
  --path ./skills
```

Then edit `skills/my-skill/SKILL.md` and validate the plugin.

## Codex

Validate:

```bash
uv run --with PyYAML python /Users/a1/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

This repo is a plugin root for Codex because it contains `.codex-plugin/plugin.json` and `skills/`.

## Claude Code

Test without installing:

```bash
claude --plugin-dir /Users/a1/Codes/my-skills
```

Install through the local marketplace:

```bash
claude plugin marketplace add /Users/a1/Codes/my-skills/claude-marketplace
claude plugin install my-skills@my-skills-local
```

The marketplace uses `claude-marketplace/plugins/my-skills` as a symlink back to this plugin root so the same source tree works for both Codex and Claude Code.

Validate:

```bash
claude plugin validate /Users/a1/Codes/my-skills
```

When you add or change skills, bump the version in both plugin manifests and the marketplace entry before reinstalling.
