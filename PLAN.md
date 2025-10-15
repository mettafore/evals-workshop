# Email Summarizer Eval Workshop – Build Plan

## Objectives
- Launch a 60-minute, hands-on workshop that teaches the Analyze → Measure → Improve loop via an email summarizer evaluation.
- Deliver reusable assets: curated Enron-based datasets, notebook stack, helper utilities, facilitation materials, and CI integration examples.
- Ensure participants leave with an automated LLM judge that detects commitment misses, incorrect metadata, and hallucinated details in summaries.

## Deliverables
1. **Dataset package** (`data/filtered_emails.csv`, `data/golden_emails.json`).
2. **Notebook stack** (`notebooks/00`–`05`) with pre-run outputs, speaker notes, and homework indicators.
3. **Helper library** (`workshop_utils.py`) exposing filtering, parsing, evaluation, and visualization helpers.
4. **Facilitation kit**: slide deck outline, rubric card, live-demo scripts, troubleshooting sheet.
5. **CI sample**: YAML snippet + README section demonstrating regression gating.
6. **Dry-run report** summarizing issues, timing, participant feedback.

## Timeline (target = 3 days)
- **Day 1**: Finalize scope, align on SME model and rubric; run filtering pipeline to publish `filtered_emails.csv` and document it in `data/README.md`.
- **Day 2**: Author notebooks `00` (HW walkthrough) and `01` (live session intro with SME/rubric coverage); outline `02`–`04` structure and prepare helper utilities scaffold.
- **Day 3**: Implement notebooks `02`–`04`, draft `05` facilitation deck, add CI sample, and assemble facilitation assets (rubric card, timing sheet); run a quick internal dry run.

## Workstreams & Tasks
### 1. Data Preparation
- Implement filtering helpers to derive per-email features (participants, quote markers, subject normalization).
- Run content filters: action-keyword confirmation, recipient caps, broadcast subject removal, subject frequency limit, quote/length heuristics, 5k character ceiling.
- Export curated slice (`data/filtered_emails.csv`) plus parsing metadata notes.

### 2. Golden Set Authoring
- Select ~40 representative emails with inline conversational context (support, sales, project updates) balancing successes/failures.
- Produce `fact_table.json` entries capturing commitments: `{task, owner, due_date, blockers}`.
- Write reference summaries aligned with the rubric (≤120 words, bullet-friendly).
- Store splits (`train/dev/test`) and document selection rationale in `data/README.md`.

### 3. Judge Development Pipeline
- Define failure taxonomy: `MissedCommitment`, `WrongOwnerOrDate`, `HallucinatedDetail`.
- Draft baseline LLM-judge prompt; collect few-shot examples from train set.
- Implement evaluation harness (precision/recall, sensitivity/specificity) using helper utils.
- Validate on dev set, lock prompt via test results, capture Rogan–Gladen walkthrough.

### 4. Notebook Production
- `00-Obtain-Candidate-Set.ipynb` (HW walkthrough): demonstrate filters, save curated CSV.
- `01-email-eval-prompt-engineering.ipynb`: GenAI eval fundamentals (definition vs. classic ML metrics, why evaluations are hard), Three Gulfs with Analyze → Measure → Improve framing, curated dataset loader with slice parameters + summary stats, interactive email explorer widget, commitment summarization problem statement, SME alignment models, rubric table, manual inspection exercise, prompt-engineering best practices checklist, starter prompt template, references & next-step signposts.
- `01a-generate-synthetic-data.ipynb` (optional homework): augmentation patterns.
- `02-open-and-axial-coding.ipynb`: manual labeling workflow, taxonomy alignment.
- `03-automated-evaluators.ipynb`: LLM-as-a-judge, programmatic checks, metric computation.
- `04-ci-golden-set.ipynb`: regression gating, YAML template, improvement backlog.
- `05-improvement-playbook.md` (slides/notes): summarize Improve-stage mechanisms and facilitation cues.
- Pre-run heavy cells; add markdown checkpoints, HW callouts, and speaker notes.

### 5. Helper Utilities
- Create `workshop_utils.py` with:
  - Email filtering and parsing functions reused across notebooks.
  - Commitment extractor (rule-based fallback for demos).
  - Metric helpers (`calc_confusion_matrix`, `estimate_true_rate`).
  - Visualization helpers (turn-based summaries, heatmaps).
- Add unit tests (`tests/test_utils.py`) covering filtering and metric math.

### 6. Facilitation Assets
- Build slide outline highlighting Three Gulfs, rubric, live-demo flow.
- Design printable rubric/annotation card (commitment checklist + failure examples).
- Prepare “bad judge” prompt variants for debugging exercise.
- Draft instructor timing sheet with cues for audience interaction.

### 7. Dry Run & Feedback
- Conduct internal rehearsal with 2–3 testers; collect timing + clarity notes.
- Log issues in `docs/dry_run_report.md` with resolution owners/dates.
- Apply fixes to notebooks, datasets, facilitation assets.

## Dependencies & Tooling
- Raw Enron dump located at `data/emails.csv` (validated checksum pending).
- Python env from repo `pyproject.toml`; ensure `jupyter`, `pandas`, `matplotlib`, `seaborn`, `ipywidgets` installed.
- Access to chosen LLM API for judge development (configure `.env` + fallback instructions for offline mode).

## Risk & Mitigation
- **PII leakage**: enforce redaction script + manual spot checks; document process.
- **Judge instability**: keep golden set diversified, include regression tests for prompt drift.
- **Time overruns**: set hard limits for notebook cell execution; cache LLM outputs locally.
- **Participant confusion**: provide quick-start guide, homework pointers, and troubleshooting appendix.

## Acceptance Criteria
- Workshop can be delivered end-to-end in 60 minutes with ≤5 minutes overhead.
- Judge achieves ≥0.80 sensitivity & specificity on test split; bias correction demonstrated.
- Participants leave with actionable Improve-stage next steps documented in handout.

## Next Steps
1. Confirm rubric + taxonomy with stakeholders (Owner: ___, Due: ___).
2. Document the filtering pipeline in `data/README.md` and publish `filtered_emails.csv` (Owner: ___, Due: ___).
3. Outline Notebook 01 sections (SME alignment, rubric, manual inspection) and assign authors (Owner: ___, Start: ___).
