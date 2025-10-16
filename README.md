# Email Summarizer Eval Workshop

Hands-on curriculum for teaching the Analyze → Measure → Improve loop on an email summarisation task. The repo bundles datasets, notebooks, a prompt library, a DuckDB-backed trace store, and a Flask-based annotation UI so facilitators can run a 60-minute workshop end-to-end.

## Repository Tour
- `notebooks/00-Obtain-Candidate-Set.ipynb` – filter raw Enron mail into `data/filtered_emails.csv`.
- `notebooks/01-email-eval-prompt-engineering.ipynb` – introduce evaluation framing, refine the prompt, then save it with the appended cell to `prompts/email_summary_prompt.txt`.
- `notebooks/01a-generate-synthetic-data.ipynb` – Homework-style synthetic generator (offline template + optional LLM path) producing `data/synthetic_emails.{csv,jsonl}`.
- `notebooks/02-open-and-axial-coding.ipynb` – analyze annotations from DuckDB, compare failure-mode coverage, and export results.
- `tools/generate_email_traces.py` – CLI that reads an email CSV, replays the saved prompt, writes request/response traces to `annotation/traces/<run_id>/`, and upserts tables in `data/email_annotations.duckdb`.
- `tools/email_annotation_app.py` + `annotation/templates/` + `annotation/static/` – keyboard-friendly annotation UI inspired by Notebook 00’s explorer (A to annotate, F to add failure modes, ←/→ to navigate).
- `sql/annotation_schema.sql` – DuckDB schema (labelers, trace runs, emails, annotations, failure modes, axial links).
- `prompts/` – current prompt text (`email_summary_prompt.txt`).
- `data/` – raw/filtered email CSVs, synthetic exports, DuckDB catalog.

## Setup
1. **Python**: 3.12+ (project targets it in `pyproject.toml`).
2. **Dependencies**: `uv pip install -r pyproject.toml` *or* `pip install duckdb ipywidgets marimo matplotlib pandas pydantic pydantic-ai`.
3. **LLM credentials**: configure Pydantic AI with your provider (e.g., set `OPENAI_API_KEY`, optionally `PYDANTIC_AI_MODEL` like `openai:gpt-4o-mini`).

## Core Workflow
1. **Prepare Data & Prompt**
   - Run Notebook 00 to materialise `data/filtered_emails.csv` (or curate your own slice).
   - Run Notebook 01 to cover eval framing, tweak the prompt, and execute the “save prompt” cell (writes to `prompts/email_summary_prompt.txt`).
2. **Optional Synthetic Seed**
   - Notebook 01a generates a 160-email synthetic grid across designation/tone/context/intent when real traces are sparse.
3. **Generate Trace Run**
   - Commit your worktree (the generator refuses to run with uncommitted changes), then run `python tools/generate_email_traces.py --emails data/filtered_emails.csv [--model provider:model_id] [--workers N]`.
   - The script calls the configured LLM via Pydantic AI (validated against the `SummaryPayload` schema), optionally parallelises the LLM calls (`--workers`), derives `run_id = git rev-parse --short HEAD`, writes JSON traces to `annotation/traces/<run_id>/trace_*.json`, copies the prompt + source CSV into that same folder, and stamps the `run_id`, prompt checksum, model name, and prompt checksum into DuckDB tables (`trace_runs`, `emails_raw`).
   - For live demos, toggle `RUN_TRACE_GENERATOR = True` inside Notebook 02 to run the same command inline.
4. **Annotate in the Browser**
   - Launch `python tools/email_annotation_app.py` and open `http://localhost:5000`.
   - Controls: `A` (add annotation; Enter saves, Esc cancels), `F` (link failure mode after at least one annotation), `←/→` (navigate emails), `Generate Failure Modes` (token-based suggestions). Selected failure modes appear as removable chips beneath the picker. All changes persist immediately to DuckDB—no manual save button.
5. **Analyze in Notebook 02**
   - Choose `filtered` vs `synthetic` dataset, verify available `run_id`s, inspect DuckDB tables, review pass/fail mix, Intent × status pivots, failure-mode/intent co-occurrence, and export CSV snapshots (`EXPORT = True`).
6. **Iterate**
   - Repeat the loop after prompt fixes: rerun Notebook 01, regenerate traces (new short SHA), re-annotate high-priority emails, and compare runs by filtering DuckDB queries on `run_id`.

## Quick Reference
- **Keyboard shortcuts** (annotation UI): `A` add note, `F` attach mode, `←/→` navigate, `Esc` cancel, `Enter` confirm.
- **Run IDs**: short Git SHA (with `-dirty` suffix if the workspace isn’t clean). They label trace folders, display in the UI, and index DuckDB tables.
- **Exports**: Notebook 02 writes `data/email_annotations_<run_id>.csv` and `data/failure_modes_<run_id>.csv` when `EXPORT = True`; include the run ID when sharing results.

## Troubleshooting
- `ModuleNotFoundError: duckdb` → install via `pip install duckdb` (added to `pyproject.toml`).
- `pydantic-ai` not installed / credentials missing → `pip install pydantic-ai`, set provider keys (`OPENAI_API_KEY`, etc.), and optionally `PYDANTIC_AI_MODEL`.
- No trace directories → rerun `tools/generate_email_traces.py` with the desired CSV.
- Empty annotation UI → ensure `data/email_annotations.duckdb` exists and contains rows for the active `run_id`.
- Comparing versions → filter Notebook 02 queries by `run_id` (each prompt change should produce a new trace run).

## Next Steps
- Expand annotations until each major failure mode has ≥20 failing examples.
- Move to Notebook 03 (future) for automated evaluator metrics once the taxonomy stabilises.
- Keep prompt/trace changes committed in Git so the short SHA continues to represent the source of truth for each run.
