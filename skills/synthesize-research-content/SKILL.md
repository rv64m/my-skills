---
name: synthesize-research-content
description: Use when a user provides papers, PDFs, notes, documentation, technical material, videos/transcripts, URLs, or raw study content and asks for a researched Markdown synthesis, study guide, literature or technical review, enriched explanation, follow-up questions, or analysis with optional Python parsing, data work, plots, SciencePlots, Seaborn, or LaTeX figures.
---

# Synthesize Research Content

## Overview

Transform user-provided source material into an evidence-grounded Markdown deliverable. Combine close reading, web research, question expansion, and optional local Python analysis so the final output is richer than a summary.

## Core Workflow

1. Clarify only when required. If the user did not specify format, infer a useful Markdown artifact: structured summary, annotated notes, study guide, technical explainer, literature review, or implementation brief.
2. Ingest the source. Extract text, tables, figures, references, transcript segments, metadata, and page or timestamp anchors when available. Track which claims come from the user-provided source versus external research.
3. Search the web. Use web search to enrich context, verify current facts, find primary sources, connect related concepts, and surface alternative explanations or critiques. Prefer papers, official documentation, standards, reputable textbooks, and project docs before blogs or secondary summaries.
4. Generate questions from the content. Produce focused questions about definitions, mechanisms, assumptions, methods, evidence, limitations, applications, prerequisites, contradictions, and open problems. Search the highest-value questions and fold the answers back into the synthesis.
5. Use a temporary Python workspace when helpful. For PDFs, tables, data extraction, plots, simulations, equations, or visual explanations, run `scripts/create_research_env.py` to create an isolated workspace. Install only the packages needed for the task.
6. Produce the Markdown output. Include headings, citations or source links, equations, tables, diagrams, and embedded figure paths when they improve understanding.

## Web Research Guidance

- Search with multiple query shapes: exact titles, key terms, author/project names, cited methods, competing approaches, and "limitations" or "critique" queries.
- Search generated questions selectively; prioritize questions whose answers would change the user's understanding.
- Cite sources with links. Clearly label inferences and unresolved uncertainty.
- Avoid padding. Every external source should add context, correction, contrast, or a useful next step.
- Respect the user's instruction if they explicitly ask for no web search, but note the limitation.

## Python Analysis Guidance

Use the environment helper when the task involves file parsing, quantitative analysis, visualization, or reproducible exploration:

```bash
python3 scripts/create_research_env.py --name research-synthesis --create-venv
```

Then activate the printed virtual environment path and install packages from the generated `requirements.txt` only if needed. Common uses include:

- Parse PDFs with `pdfplumber`, `pypdf`, or `pymupdf`
- Extract tables and clean data with `pandas`
- Plot concepts, comparisons, distributions, or workflows with `matplotlib`, `seaborn`, and `scienceplots`
- Render formulas with Matplotlib mathtext; use full LaTeX only when a TeX installation is available
- Save generated figures under the temporary workspace and embed absolute paths in the Markdown output

## Markdown Output Pattern

Adapt the structure to the user's instruction. A strong default:

```markdown
# Title

## Executive Summary

## Source-Derived Notes

## Web-Enriched Context

## Key Concepts and Relationships

## Questions Investigated

## Analysis or Figures

## Limitations and Open Questions

## References
```

For learning material, include prerequisite concepts, worked examples, checkpoints, and exercises. For academic papers, include research question, method, contribution, assumptions, findings, limitations, related work, and reproducibility notes. For technical docs, include architecture, APIs, tradeoffs, pitfalls, examples, and implementation implications.

## Quality Bar

- Keep source-derived claims separate from web-enriched claims when the distinction matters.
- Do not fabricate citations, page numbers, timestamps, equations, or figure interpretations.
- Use short quotes only when exact wording matters; otherwise paraphrase.
- Prefer concrete diagrams, tables, equations, plots, or examples over vague explanation.
- End with useful next questions or study directions when the user is trying to learn systematically.

## Optional Reference

For longer or more complex synthesis tasks, read `references/research-workflow.md` for a compact checklist of extraction, search, question-generation, and output patterns.
