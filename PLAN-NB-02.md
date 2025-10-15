# PLAN for Notebook 02 – Open & Axial Coding With DuckDB Backing

## 1. Goals
- Explain Chapter 3’s **open → axial** coding loop using the synthetic/real email dataset produced in Notebooks 00/01a.
- Direct facilitators to perform actual annotations inside a dedicated web UI (inspired by `masala-embed/esci-dataset/annotation`), not inside Jupyter cells.
- Persist annotations and taxonomy decisions in DuckDB so later notebooks (automation + CI) can query consistent labels.

## 2. Notebook 02 Outline
0. **Prerequisite: Generate Annotation Traces**
   - Instruct users to choose the source email file (`../data/filtered_emails.csv` or another exported slice) and run `python tools/generate_email_traces.py --emails ../data/filtered_emails.csv --out annotation/traces/` (script modeled after `recipe-chatbot/scripts/bulk_test_traces.py`).
   - Each trace run should derive a `run_id` from `git rev-parse --short HEAD`; traces are written under `annotation/traces/{run_id}/trace_*.json` so the commit-version linkage is obvious without extra tooling.
   - Include an optional notebook cell (`!python ../tools/generate_email_traces.py --emails {DATA_SOURCE_PATH} --out ../annotation/traces`) so workshop facilitators can demo trace generation live without leaving Jupyter; surface progress info within the notebook via captured stdout.
   - Script responsibilities:
     - Load emails, feed them through the summarizer (or placeholder prompt) to produce trace JSON with request/response history.
    - Reuse the finalized prompt saved by Notebook 01 (`../prompts/email_summary_prompt.txt`); when ingesting traces into DuckDB simply stamp rows with the current `run_id` so the prompt version is implied without extra metadata files.
     - Persist traces under `annotation/traces/{run_id}/trace_*.json` with deterministic naming.
     - Optionally register new emails into DuckDB (`emails_raw`) for downstream joins and stamp each row with the `run_id`.
   - Notebook references assume traces are present before launch; provide quick diagnostic cell to count files and raise instructions if missing.

1. **Title + Context Recap**
   - Homework-style heading (`Homework 02: Open & Axial Coding Walkthrough`).
   - Short reminder of the Analyze phase and why we use grounded theory before automation.

2. **Setup Cell Block**
   - Imports: `pandas`, `duckdb`, `pathlib`, `json`.
   - Config: paths for `../data/filtered_emails.csv` and `../data/synthetic_emails.csv`, DuckDB file location `../data/email_annotations.duckdb`.
   - Guard rails: raise helpful error if datasets are missing, mimic Notebook 00/01 style.

3. **Data Preparation Section**
   - Provide a parameter/Widget (`DATA_SOURCE = "filtered" | "synthetic"`) so facilitators pick between `filtered_emails.csv` (real) or `synthetic_emails.csv` (Notebook 01a output).
   - Load the chosen dataset, normalize key fields (`email_id`, `subject`, `body`, composite metadata).
   - Verify prerequisite traces exist: count `annotation/traces/{run_id}` folders; if empty, surface reminder to run `tools/generate_email_traces.py`.
   - Display a few samples so annotators see exactly what will surface in the UI.

4. **Link to Annotation Tool**
   - Markdown explanation of the Flask app derived from `/masala-embed/esci-dataset/annotation/app.py` + `templates/annotate.html`, styled with the ipywidget email card from Notebook 00 (subject header, metadata chips, commitments block, quoted thread styling).
   - Controls to document in the plan:
      - `A`: open annotation input overlay; `Enter` saves, `Esc` cancels. Saved annotations render in a right-hand panel.
      - `F`: open failure-mode picker. Users can select existing failure modes or create new ones (but only after at least one annotation exists for the trace). Chosen failure modes appear in a "Selected Failure Modes" list directly beneath the picker with quick-remove chips.
      - Left/Right arrow keys (or on-screen buttons) navigate to the previous/next email trace to keep throughput high during workshops.
      - `Generate Failure Modes` button (per trace): runs an optional LLM helper that proposes failure-mode candidates based on the current trace’s saved annotations; annotators must explicitly accept/reject each suggestion before attaching it.
    - Emphasize that the backend stores every annotation/failure-mode change immediately in DuckDB (no manual save button), so workshop attendees see live persistence just like the masala-embed tool.
   - Usage instructions:
      1. Run `python tools/email_annotation_app.py --database` (script we will scaffold) from repo root.
      2. Visit `http://localhost:5000`, pick your `labeler_id` (or create a new one), then label emails with keyboard shortcuts and progress tracking; the active `run_id` (short Git SHA) should display in the UI chrome so annotators know which prompt/version they’re reviewing.
   - Provide screenshot placeholder or textual description of layout to match the enhanced annotation tool style.

5. **DuckDB Storage Schema (Explained in Notebook, Created via Helper Script)**
   - Present ER outline:
     - `labelers(labeler_id PRIMARY KEY, name, email)` — manage annotator identities/permissions.
     - `trace_runs(run_id PRIMARY KEY, prompt_path, prompt_checksum, source_csv, generated_at)` — `run_id` uses the short Git SHA for human-friendly provenance.
     - `emails_raw(email_id PRIMARY KEY, subject, body, metadata JSON, run_id)`
     - `annotations(annotation_id PRIMARY KEY, email_id, labeler_id, open_code TEXT, pass_fail INTEGER, run_id, created_at TIMESTAMP)`
     - `failure_modes(failure_mode_id PRIMARY KEY, slug, definition, examples JSON)`
     - `axial_links(annotation_id, failure_mode_id)` — many-to-many bridge between raw notes and taxonomy.
   - Notebook will show `duckdb.sql("DESCRIBE ...")` queries so facilitators can confirm migrations ran.

6. **Open Coding Walkthrough (Inside Notebook)**
   - Use pandas to read `annotations` table after a labeling session (filterable by `run_id` so you can compare commits).
   - Demonstrate filters: first-failure principle, sample pivot of open codes by intent/tone.
   - Highlight Chapter 3 heuristics (stop when no new codes appear, binary pass/fail columns) and show how the short `run_id` makes before/after comparisons trivial.

7. **Axial Coding Walkthrough**
   - Show how saved annotations appear in the UI’s right rail and in DuckDB.
   - Demonstrate assigning failure modes via `F` shortcut or curated list; highlight guardrails (cannot attach a failure mode unless at least one annotation exists for that trace). Selected modes should render immediately beneath the picker so annotators can confirm the active set or remove items inline.
   - Notebook section runs queries to show coverage (counts by failure mode, co-occurrence matrices) grouped by `run_id`. If users clicked “Generate Failure Modes,” show how to review the LLM-suggested list, accept/reject items, and persist chosen modes under the current `run_id`.
   - Encourage annotators to iterate: merge, split, refine definitions based on observed annotations.

8. **Export & Handoff**
   - Write flattened CSV `../data/email_annotations_export.csv` for stakeholders.
   - Persist taxonomy snapshot `../data/failure_mode_taxonomy.json` from DuckDB query.
   - Provide checklist for readiness to proceed to Notebook 03 (e.g., ≥20 failing examples per major mode) and remind facilitators to note the `run_id`/prompt version when sharing exports.

## 3. Supporting Assets To Build (Outside Notebook)
- `tools/generate_email_traces.py`: CLI patterned after `recipe-chatbot/scripts/bulk_test_traces.py` for producing request/response trace JSON from a selected email CSV.
- `tools/email_annotation_app.py`: thin wrapper around the masala-embed Flask app tuned for email fields + DuckDB.
- `annotation/templates/email_annotate.html`: forked from `annotate.html` with columns adjusted for email subject/body and commitment checklist hints.
- `annotation/static/...`: optional CSS/JS reuse to support keyboard shortcuts and DuckDB writebacks.
- DuckDB migration helper `sql/annotation_schema.sql` defining the tables listed above (including the `trace_runs` table and `run_id` columns).

## 4. DuckDB Integration Plan
1. Notebook 02 runs `duckdb.sql` to ensure schema exists (idempotent `CREATE TABLE IF NOT EXISTS`).
2. Data ingestion utility (`tools/generate_email_traces.py` or equivalent CLI) inserts emails into `emails_raw` when traces are generated, stamping each row with the `run_id` (short Git SHA) so Notebook 02 can join annotations against metadata.
3. Annotation UI writes rows into `annotations` (and `axial_links` when taxonomy assignment happens).
4. Notebook queries `annotations` + `emails_raw` joins to power open/axial coding visuals.

## 5. Open Questions for Refinement
- Confirm whether we preload `synthetic_emails.csv` into DuckDB automatically or ask facilitators to trigger ingestion.
- Determine minimum fields the annotation UI should expose (e.g., do we show designation/tone metastats? commitment scaffolds?).
- Decide on default label choices: pass/fail + freeform open code? or multi-select failure types?
- Align on due-date handling—should annotators capture structured corrections or just open-code text?

The plan above keeps Notebook 02 explanatory and analytical while delegating heavy annotation UX to a specialized tool, mirroring Chapter 3 best practices and the Homework 2 playbook.
