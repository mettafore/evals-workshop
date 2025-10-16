# PLAN for Notebook 03 – Automated Evaluators & LLM Judge

## 1. Goals
- Build an end-to-end **Measure**-phase workflow that converts human annotations from Notebook 02 into an aligned, bias-corrected LLM judge.
- Quantify failure prevalence on new email traces using Rogan–Gladen bias correction and bootstrap confidence intervals (Chapter 5 guidance).
- Package judge assets (prompt, metrics, corrected rates) for reuse by downstream automation/CI.

## 2. Prerequisites
- `data/filtered_emails.csv` (with `email_hash`) produced by Notebook 00.
- `data/synthetic_emails.csv` if you intend to include synthetic traces (optional).
- An annotation table in DuckDB (`email_annotations.duckdb`) populated via Notebook 02 / annotation app with columns `email_hash`, `open_code`, `pass_fail`, `run_id`, `created_at`.
- Evaluators rely on the **same run_id** used during annotation; ensure the DuckDB file is up to date before opening Notebook 03.
- Environment dependencies: `pandas`, `numpy`, `pydantic`, `pydantic-ai`, `scipy` (for bootstrap utilities), `duckdb`, `plotly` (optional charts).
- Valid LLM credentials (e.g., `OPENAI_API_KEY`) for the judge prompt calls.

## 3. Notebook Outline
1. **Header & Objectives**
   - Brief reminder of Measure-phase goals and linkage to Chapter 5.
2. **Setup & Imports**
   - Import `pandas`, `duckdb`, `numpy`, `random`, `pydantic_ai.Agent`, helper utilities.
   - Define data paths and results directories (e.g., `results/judge/`).
3. **Configuration Widgets**
   - Dropdown/text inputs for `run_id` selection, minimum annotation timestamp filters, optional dataset (filtered vs synthetic), judge prompt template path (`prompts/email_judge_prompt.txt` default).
4. **Load Annotated Data**
   - Join `annotations` with `emails_raw` on `email_hash` for the selected `run_id`.
   - Display counts, pass/fail balance, and review sample disagreements.
5. **Create or Load Splits**
   - Option A: Auto-generate `train/dev/test` splits with target counts (e.g., 20/40/40) ensuring stratification by `pass_fail`.
   - Option B: Load pre-existing splits from `data/judge_splits/*.csv` if present.
   - Persist new splits to disk so future runs are stable.
6. **Inspect Split Quality**
   - Show class balance per split.
   - Display first few examples from each partition for transparency.
7. **Design Judge Output Schema**
   - Define `JudgeResponse` Pydantic model with fields `reasoning: str` and `answer: Literal["Pass", "Fail"]`.
8. **Draft Judge Prompt**
   - Provide an editable text area containing a scaffold (task definition, pass/fail criteria, structured output instructions).
   - Include placeholders for inserting few-shot examples from the training split.
9. **Build Few-Shot Examples**
   - Helper cell to curate training examples (select `n_pass` and `n_fail` cases) and render them into the prompt context.
10. **Call Judge (Single Example)**
    - Utility function to render the prompt, call `Agent.run_sync`, and display structured output for a single email (debugging aid).
11. **Batch Evaluation Utilities**
    - Functions to run the judge over a dataframe (dev or test), caching responses to `results/judge/cache/` for reproducibility.
12. **Evaluate on Dev Set**
    - Compute confusion matrix, TPR, TNR using dev labels.
    - Present metrics in table and quick bar chart.
    - List disagreements with links back to raw email text for inspection.
13. **Iterative Refinement Area**
    - Markdown guidance (Chapter 5 loop: inspect → refine → re-test).
    - Provide re-run buttons/cells to regenerate metrics after editing the prompt.
14. **Lock Final Prompt & Test Evaluation**
    - Once satisfied, freeze prompt text (write to `prompts/email_judge_prompt_final.txt`).
    - Run judge on the **test split**, record TPR/TNR, store confusion matrix to `results/judge/test_metrics.json`.
15. **Run Judge on Unlabeled Traces**
    - Choose dataset (rest of filtered emails or synthetic set) to estimate prevalence.
    - Cache raw predictions with columns `[email_hash, run_id, judge_answer, judge_reasoning, prompt_version]`.
16. **Bias Correction & Confidence Interval**
    - Implement Rogan–Gladen formula `theta_hat = (p_obs + TNR - 1) / (TPR + TNR - 1)`.
    - Bootstrap (e.g., 10,000 resamples) to derive 95% CI.
    - Display corrected rate and interval.
17. **Reporting Artifacts**
    - Summarize final metrics (TPR/TNR, corrected success rate, CI) in Markdown and write JSON report (e.g., `results/judge/final_report.json`).
    - Save final judge prompt to `results/judge/judge_prompt.txt` for audit.
    - Optional: generate a short PDF/HTML summary for stakeholders.
18. **Next Steps & Checklist**
    - Remind the user to document prompt changes (Git commit with `prompts/email_judge_prompt_final.txt`).
    - Suggest verifying on a second run_id or fresh annotations when available.

## 4. Supporting Assets To Add
- `prompts/email_judge_prompt.txt` – initial scaffold for the judge.
- `results/judge/README.md` – describes cached responses and metric files.
- Utility module (optional) `notebooks/utils/judge_helpers.py` for shared code (render prompt, compute bias correction, bootstrap).
- Example template for structured output instructions (Chapter 5 style) to include in Notebook 03.

## 5. Key Functions to Implement
- `render_judge_prompt(example, few_shots, template) -> str`
- `run_judge(agent, prompt) -> JudgeResponse`
- `evaluate_split(df, predictions) -> metrics dict`
- `bootstrap_confidence_interval(test_labels, predictions, num_samples=10000)`
- `bias_correct(p_obs, tpr, tnr)` with clipping/validation (warn if denominator near zero).

## 6. Open Questions / Decisions
- Should we support multiple failure modes simultaneously (loop over selected taxonomy items) or focus on one at a time? (Default: one-at-a-time; require user to filter annotations accordingly.)
- Do we want to include cost tracking (LLM token usage) in the report? (Optional.)
- How to handle judge caching when prompt changes? (Store prompt checksum with cached predictions and invalidate if checksum differs.)
- Do we expose a convenience cell to push final metrics into a `results/judge/metrics_latest.json` file for CI pick-up?

## 7. Deliverables from Notebook 03
- Final judge prompt (`results/judge/judge_prompt.txt`).
- Dev & test evaluation metrics (JSON + human-readable tables).
- Bias-corrected success rate with confidence interval.
- Raw judge predictions on selected unlabeled traces.
- Markdown summary cell describing results, next steps, and any manual actions required (e.g., re-running annotations if prompt drifts).

This plan mirrors the structure outlined in Chapter 5 (judge development, accuracy estimation, bias correction) and the HW3 reference pipeline (splits, prompt iteration, final evaluation). Implementing the above notebook will transition the workshop from manual annotations (Notebook 02) to automated prevalence measurement (Notebook 03).
