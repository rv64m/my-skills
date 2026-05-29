# Research Workflow Checklist

## Intake

- Identify the user's requested output type, audience, depth, language, and deadline if stated.
- Extract bibliographic or source metadata: title, authors, date, version, URL, pages, timestamps, repository, or product version.
- Preserve anchors for later citation: page numbers, sections, figure numbers, equation numbers, timestamps, or line references.

## Source Extraction

- PDF: extract text first, then tables and figures if relevant. Use OCR only when text extraction fails.
- Paper: map abstract, problem, method, results, limitations, related work, and references.
- Technical docs: map concepts, APIs, parameters, examples, architecture, constraints, and known pitfalls.
- Video/transcript: segment by topic and timestamp; distinguish spoken claims from visual evidence when possible.
- Notes: normalize headings, recover implied questions, and mark unclear or incomplete areas.

## Web Search Expansion

- Search exact source title or URL first.
- Search key terms plus "overview", "survey", "tutorial", "limitations", "critique", and "comparison".
- Search named methods, datasets, standards, libraries, equations, authors, products, or protocols.
- Prefer primary sources: papers, official docs, standards, source repos, release notes, or institutional pages.
- Use secondary sources only when they clarify, contrast, or contextualize the primary material.

## Question Generation

Generate questions across these categories:

- What is the source trying to solve or explain?
- What prerequisite concepts does the reader need?
- What assumptions make the argument or technique work?
- What evidence supports the main claims?
- What would falsify or weaken the claims?
- What related work, competing method, or adjacent tool matters?
- What practical implications, examples, or failure modes should the reader know?
- What can be visualized, simulated, tabulated, or calculated?

Search only the questions that are likely to change the final answer.

## Analysis and Figures

- Use a temporary workspace for extracted files, generated datasets, and plots.
- Prefer simple, labeled figures over ornamental graphics.
- Use Seaborn for statistical comparisons and distributions.
- Use SciencePlots for publication-like Matplotlib styling when it improves readability.
- Use LaTeX rendering only when the environment supports it; Matplotlib mathtext is often enough.
- Export figures as PNG or SVG and embed absolute paths in the final Markdown when the client can render local images.

## Markdown Deliverables

- Start with the answer the user asked for, then add supporting detail.
- Keep "source says" and "external context says" separate when provenance affects trust.
- Use tables for comparisons, definitions, assumptions, and evidence maps.
- Include a References section with source links and a brief note on what each source contributed.
- End with open questions, further reading, or exercises when the user is learning systematically.
