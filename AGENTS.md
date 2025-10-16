# Repository Guidelines

## Project Structure & Module Organization
- **notebooks/**: Jupyter notebooks for each workshop phase (Notebook 00–03). Follow numerical order when extending.
- **tools/**: CLI utilities (e.g., `generate_email_traces.py`, `email_annotation_app.py`) used by notebooks. Keep helper modules here.
- **annotation/**: Flask UI (templates, static assets) for manual annotation. Mirrors Notebook 02 instructions.
- **data/**: CSV inputs, generated splits, and DuckDB database. Never commit PII.
- **prompts/**: Template files for summarizer and judge prompts. Add versioned filenames when prompts evolve.
- **sql/**: Schema and migration helpers (e.g., `annotation_schema.sql`).
- **results/**: Output artifacts (metrics, cached predictions). Organize by run_id/prompt version.

## Build, Test, and Development Commands
- `make ruff-check`: Run Ruff linting on Python files (excludes notebooks).
- `make ruff-fix`: Auto-fix lint issues where possible.
- `make format` / `make format-check`: Apply or verify Ruff formatter.
- `python tools/generate_email_traces.py --emails ... --prompt ...`: Regenerate traces for a prompt/model combination.
- `python tools/email_annotation_app.py`: Launch annotation UI at `http://localhost:5000`.

## Coding Style & Naming Conventions
- Python files follow Ruff defaults: 4-space indent, PEP 8 naming (`snake_case` for functions/files, `PascalCase` for classes).
- Notebooks: Start filenames with two-digit order (`00-`, `01-`, etc.) and keep cells lightweight.
- Prompts: Version filenames explicitly (e.g., `email_summary_prompt_v2.txt`) and pass via `--prompt`.

## Testing Guidelines
- Lint/format checks serve as lightweight “tests.” Run `make ruff-check` before commits.
- Manual notebook validation: execute from top to bottom; ensure widgets have sensible defaults.
- When adding unit tests (future), place under `tests/` and align with `pytest` discovery (`test_*.py`).

## Commit & Pull Request Guidelines
- Commit messages: imperative mood (`Add judge bootstrap helper`, `Refine prompt template`). Reference run_id/prompt version when relevant.
- Pull Requests should include:
  - Summary of changes and affected notebooks/tools.
  - Verification steps (commands run, notebook cells executed).
  - Screenshots or metrics snapshots when UI/judge outputs change.
- Force pushes allowed only for history rewrites (e.g., removing sensitive files). Notify teammates.
