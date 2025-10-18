# Notebook 03 Plan: Automated Evaluators for the Email Summarizer

## Goal
Author `03-automatic-evaluators.ipynb` as a theory-first guide that anchors automated evaluation concepts in the email summarizer use case.

## Section Outline
1. **Why Automated Evaluators?**  
   - Define automated evaluators; motivate with summarizer iteration speed.  
   - Connect to Analyze → Measure → Improve loop.
2. **Reference-Free vs Reference-Based Metrics**  
   - Summarizer-specific definitions and contrasting examples (tone vs key facts).  
   - Quick comparison table grounded in workshop datasets.
3. **Programmatic Evaluators for Summaries**  
   - Theory: when deterministic rules suffice.  
   - Code example: informal-tone detector using keyword heuristics on sample summaries + action items.  
   - Display example outputs only (no full pipeline).
4. **LLM-as-Judge Evaluators**  
   - Why we need them for nuanced summarizer criteria (faithfulness, action coverage).  
   - Prompt anatomy tailored to "Decision Coverage" judge.  
   - Discuss JSON output schema and failure logging.
5. **Judge Alignment Workflow**  
   - Simulated dataset of 100 labeled traces.  
   - Split ratios (train 15%, dev 40%, test 45%) matching reference guidance.  
   - Baseline few-shot examples → compute TPR/TNR confusion matrix.  
   - Swap-in improved few-shot examples → show accuracy lift.  
   - Emphasize reviewing disagreements during iteration.
6. **Bias Correction & Confidence Intervals**  
   - Use judge stats to correct observed success rate on a mock production batch.  
   - Bootstrap CI snippet.
7. **Takeaways & Next Steps**  
   - How to plug into actual workshop traces.  
   - Pointers to future notebook and tooling.

## Assets Needed
- Synthetic labeled summaries (100 rows) with pass/fail labels for at least one nuanced criterion.  
- Example few-shot prompt text under `prompts/` or embedded in notebook cells.  
- Lightweight helper functions for splitting, confusion matrix, and correction math.

## Open Questions / TBD
- Finalize which criterion the LLM judge targets (e.g., "captures all action items").  
- Decide whether to keep placeholder LLM responses or integrate with mock API wrapper identical to `tools/` style.
