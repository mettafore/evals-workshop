# Application-Centric AI Evals - Complete Course Summary

**Authors**: Shreya Shankar and Hamel Husain
**Focus**: Evaluating LLM applications (not foundation models)
**Framework**: Analyze-Measure-Improve Lifecycle

---

## Part 1: Foundations

### Chapter 1: Introduction - The Three Gulfs

**Core Problem**: How do we assess if an LLM pipeline performs adequately and diagnose where it's failing?

#### The Three Gulfs Model

1. **Gulf of Comprehension** (Developer → Data)
   - Can't manually review thousands of inputs/outputs at scale
   - Challenge: Understanding data distribution AND pipeline behavior on that data
   - Solution: Systematic sampling and error analysis

2. **Gulf of Specification** (Developer → LLM Pipeline)
   - Gap between what you mean vs. what you specify
   - Underspecified prompts force LLM to "guess" intent
   - Solution: Detailed, explicit instructions informed by looking at data

3. **Gulf of Generalization** (Data → LLM Pipeline)
   - Even with clear prompts, LLMs behave inconsistently across inputs
   - Will always exist to some degree (no model is perfect)
   - Solution: Iterative testing, architectural improvements, fine-tuning

#### The Analyze-Measure-Improve Lifecycle

```
ANALYZE → MEASURE → IMPROVE → (repeat)
   ↓          ↓          ↓
Identify    Quantify   Fix & Iterate
failures    patterns   systematically
```

- **Analyze**: Inspect pipeline on representative data, identify failure modes (tackles Comprehension)
- **Measure**: Develop evaluators to quantify failures (provides data for prioritization)
- **Improve**: Fix prompts (Specification) and enhance generalization (architecture, fine-tuning)

**Critical principle**: "If you are not willing to look at some data manually on a regular cadence you are wasting your time with evals."

---

### Chapter 2: LLMs, Prompts, and Evaluation Basics

#### LLM Limitations

1. **Algorithmic**: No loops/recursion → can't do arbitrary-precision arithmetic, graph traversal
2. **Reliability**: Probabilistic outputs, extremely prompt-sensitive
3. **Factuality**: No notion of truth → hallucinations

**Mitigation**: Chain-of-Thought prompting, external tools (calculators, RAG, code interpreters)

#### Effective Prompting (7 Components)

1. Role & Objective
2. Instructions / Response Rules (clear, explicit)
3. Context
4. Examples (few-shot)
5. Reasoning Steps (Chain-of-Thought)
6. Output Formatting Constraints
7. Delimiters & Structure

**Key**: Prompting is iterative. Avoid auto-optimization tools early (forces you to clarify thinking).

#### Evaluation Metrics

**Reference-Based** (compare to ground truth)
- Examples: Exact match, SQL execution results, unit tests
- Use when: Development, offline testing, ground truth feasible

**Reference-Free** (check properties/rules)
- Examples: No speculation in summary, code compiles, adheres to brand voice
- Use when: Production, subjective outputs, multiple valid responses

**Important**: Be extremely skeptical of generic metrics. Red flag = dashboard with "{hallucination, helpfulness}_score".

#### Eliciting Labels

1. **Direct Grading**: Assess single output against rubric (absolute quality)
2. **Pairwise Comparison**: Choose better of two outputs (relative quality, easier than grading)
3. **Ranking**: Order 3+ outputs (more granular)

---

## Part 2: Analysis Phase

### Chapter 3: Error Analysis

**Goal**: Systematically identify and categorize failure modes using **grounded theory** approach from qualitative research.

#### Process

**Step 1: Create Starting Dataset**
- Collect 50-200 traces from production or synthetic generation
- Ensure diversity (edge cases, common patterns, failures, successes)
- Start small, expand iteratively

**Step 2: Open Coding**
- Read 20-50 traces, label failure modes as you discover them
- Use descriptive names (e.g., "Wrong_Company_Name_Extracted")
- Keep labels atomic (one issue per label)
- Document examples and edge cases

**Step 3: Axial Coding**
- Group related codes into higher-level categories
- Create hierarchy/taxonomy of failure modes
- Example: "Extraction_Errors" → {Wrong_Entity, Missing_Entity, Hallucinated_Entity}

**Step 4: Label Full Dataset**
- Apply structured taxonomy to all traces
- Multiple labels per trace OK

**Step 5: Iterate & Refine**
- As you label more, refine taxonomy
- Split vague categories, merge duplicates

#### Tools & Artifacts

- Spreadsheet or annotation tool
- **Axial codes CSV**: Maps atomic codes to higher-level categories
- Running example: Real Estate CRM Assistant (email → structured contact info)

**Common Pitfalls**:
- Starting with too large a dataset
- Codes too vague/broad
- Not documenting examples
- Skipping iteration

---

### Chapter 4: Collaborative Evaluation Practices

**When to collaborate**: Multiple stakeholders, subjective criteria, compliance requirements

#### 9-Step Collaborative Workflow

1. Identify collaborators (domain experts, stakeholders)
2. Draft initial rubric (simple, binary when possible)
3. Independent annotation (small batch, 20-30 traces)
4. Measure agreement (Cohen's Kappa)
5. Alignment session (discuss disagreements)
6. Refine rubric
7. Re-annotate to verify improvement
8. Scale annotation
9. Connect to automated evaluators

#### Inter-Annotator Agreement (IAA)

**Cohen's Kappa** (for 2 annotators):
```
κ = (p_o - p_e) / (1 - p_e)
```
- p_o = observed agreement
- p_e = expected agreement by chance

**Interpretation**:
- κ < 0.20: Poor
- 0.21-0.40: Fair
- 0.41-0.60: Moderate
- 0.61-0.80: Substantial
- 0.81-1.00: Almost perfect

**For 3+ annotators**: Use Fleiss' Kappa or Krippendorff's Alpha

#### Resolving Disagreements

- Have "benevolent dictator" make final call OR
- Majority vote OR
- Exclude contentious examples

**Common Pitfalls**:
- Overly complex rubrics
- No alignment sessions
- Ignoring low IAA scores
- Not documenting rationale

---

## Part 3: Measurement

### Chapter 5: Implementing Automated Evaluators

**Goal**: Translate qualitative insights from analysis into quantitative, scalable metrics

#### LLM-as-Judge Framework

**4 Essential Components**:

1. **Clear Criterion** (what aspect of quality?)
2. **Evaluation Context** (input, output, optionally reference)
3. **Structured Output** (JSON with verdict + reasoning)
4. **Explicit Instructions** (step-by-step evaluation process)

**Example template**:
```
You are evaluating whether a summary is faithful to the source.

Input: [SOURCE_TEXT]
Output: [SUMMARY]

Evaluate step-by-step:
1. Identify claims in summary
2. Verify each claim against source
3. Determine if any claims are unsupported

Respond in JSON:
{
  "faithful": true/false,
  "reasoning": "..."
}
```

#### Data Splits

- **Golden set** (50-100 examples, human-labeled): Design LLM-judge prompt
- **Validation set** (50-100 examples, human-labeled): Validate judge performance
- **Eval set** (larger, can be unlabeled): Run automated eval

#### Iterative Refinement

1. Write initial judge prompt
2. Run on golden set
3. Analyze false positives/negatives
4. Refine prompt
5. Validate on validation set
6. Deploy

#### Handling Imperfect Judges

Use **Rogan-Gladen bias correction** to estimate true success rate:

```python
def estimate_true_rate(observed_rate, sensitivity, specificity):
    """
    sensitivity = P(judge says PASS | actually PASS)
    specificity = P(judge says FAIL | actually FAIL)
    """
    return (observed_rate + specificity - 1) / (sensitivity + specificity - 1)
```

Calculate sensitivity/specificity from validation set.

**Common Pitfalls**:
- Not using data splits
- Judge prompt too vague
- Skipping bias correction
- Treating judge verdicts as ground truth

---

### Chapter 6: Evaluating Multi-Turn Conversations

**Challenge**: Failures can accumulate or emerge only after multiple turns

#### Three Evaluation Levels

1. **Session-Level**: Overall conversation success (Pass/Fail for entire conversation)
2. **Turn-Level**: Individual response quality (easier to identify specific failures)
3. **Coherence/Consistency**: Across turns (remembering context, not contradicting)

#### Practical Strategies

**1. Truncation**
- Evaluate prefixes of varying lengths
- Identify which turn introduced failure
- Example: 5-turn conversation → evaluate turns 1-3, then 1-4, then 1-5

**2. Perturbation**
- Inject controlled variations to isolate multi-turn dependencies
- Example: Shuffle turn order (if fails, order matters)

**3. Compare Single-Turn vs Multi-Turn**
- Re-evaluate problematic turns in isolation
- If passes solo but fails in conversation → multi-turn issue

#### Automated Evaluation

Use LLM-as-judge with full conversation context:
```
Conversation history: [TURNS 1-N]
Evaluate: Does Turn N contradict earlier turns?
```

**Common Pitfalls**:
- Only evaluating final turn
- Not tracking context window limits
- Ignoring accumulated errors

---

### Chapter 7: Evaluating RAG (Retrieval-Augmented Generation)

**Two-Stage Process**: Retrieve relevant docs → Generate response using docs

#### Retrieval Metrics

Need **(query, relevant_doc_ids)** pairs. Generate via:
- LLM creates queries for specific documents
- Mine from logs (users clicking specific results)

**Key Metrics**:

1. **Precision@k**: Fraction of top-k results that are relevant
   ```
   P@k = (# relevant in top-k) / k
   ```

2. **Recall@k**: Fraction of all relevant docs in top-k
   ```
   R@k = (# relevant in top-k) / (total # relevant)
   ```

3. **MRR (Mean Reciprocal Rank)**: Rewards high-ranking relevant docs
   ```
   MRR = average(1 / rank_of_first_relevant)
   ```

4. **NDCG@k**: Accounts for graded relevance (0-2 scale)
   ```
   DCG@k = Σ (2^relevance - 1) / log2(position + 1)
   NDCG@k = DCG@k / IDCG@k  (normalized)
   ```

#### Chunking Strategies

Evaluate by comparing retrieval metrics across:
- Fixed-size chunks (256, 512, 1024 tokens)
- Semantic chunking (by paragraph, section)
- Overlapping vs non-overlapping

**Run experiments**: Which chunking yields highest MRR/NDCG@k?

#### Generation Quality

**ARES Framework** (Automated RAG Evaluation):
1. **Context Relevance**: Are retrieved docs relevant to query?
2. **Answer Faithfulness**: Does answer stick to retrieved docs?
3. **Answer Relevance**: Does answer address the query?

Use LLM-as-judge for each dimension.

**Common Pitfalls**:
- Not creating (query, doc) test pairs
- Only evaluating generation (ignoring retrieval)
- Fixed chunking without experimentation
- Conflating retrieval failures with generation failures

---

## Part 4: Domain-Specific Techniques

### Chapter 8: Specific Architectures and Data Modalities

#### Tool Calling

**4-Stage Failure Analysis**:
1. **Planning**: Did LLM decide to call the right tool?
2. **Argument Generation**: Are tool arguments correct/valid?
3. **Execution**: Did tool run without error?
4. **Interpretation**: Did LLM correctly use tool output?

**Evaluate each stage separately** to pinpoint failures.

#### Agentic Systems

**Spectrum of Agency**:
- Simple: Single tool call
- Moderate: Multi-turn conversation with tool use
- High: Autonomous task decomposition + planning

**Evaluation considerations**:
- Trajectory analysis (visualize decision tree)
- Efficiency (did agent take shortest path?)
- Safety (did agent respect constraints?)

#### Multi-Step Pipeline Debugging

**Transition Failure Matrix** (like your HW5!):
- Rows: Last success state
- Columns: First failure state
- Identify common failure transitions

**Heat-map visualization** reveals bottlenecks.

#### Non-Text Modalities

**Images**:
- Describe image in prompt, ask for description/analysis
- Check if key visual elements are mentioned

**Long Documents / PDFs**:
- Test attention across document sections
- "Needle in haystack" tests (insert fact, check retrieval)

---

## Part 5: Production & Improvement

### Chapter 9: CI/CD for LLM Applications

#### CI: Continuous Integration (Known Unknowns)

**Purpose**: Prevent regressions

**Components**:
1. **Golden dataset** (50-500 examples, human-labeled)
2. **Automated evals** (reference-based + reference-free)
3. **Regression tests** (run on every code/prompt change)
4. **Performance thresholds** (e.g., "95% pass rate")

**When to run**: Pre-commit, pre-deploy

#### CD: Continuous Deployment (Unknown Unknowns)

**Purpose**: Monitor production, catch novel failures

**Strategies**:

1. **Online Monitoring**
   - Sample production traffic (1-10%)
   - Run automated evals asynchronously
   - Track metrics over time (dashboards, alerts)

2. **Guardrails**
   - Run fast evals synchronously (in critical path)
   - Block/retry/fallback if eval fails
   - Example: Check for PII before showing response

3. **Shadow Mode**
   - Run new version alongside prod
   - Compare outputs without affecting users
   - Gradual rollout based on eval performance

#### The Continuous Improvement Flywheel

```
Production Traffic
       ↓
    Monitor
       ↓
  Discover new failures
       ↓
  Add to golden set
       ↓
  Improve pipeline
       ↓
  Deploy
       ↓
(repeat)
```

**Key Differences: LLMOps vs Traditional MLOps**:

| Aspect | Traditional MLOps | LLMOps |
|--------|------------------|---------|
| Metrics | Accuracy, F1, AUC | Task-specific, often subjective |
| Failures | Distribution shift | Prompt sensitivity, hallucinations |
| Debugging | Feature importance | Trace inspection, prompt refinement |
| Iteration | Retrain model | Adjust prompts, add examples, change architecture |

**Common Pitfalls**:
- No golden dataset
- Only monitoring generic metrics
- Not sampling production data
- Treating LLM apps like traditional ML

---

### Chapter 10: Interfaces for Continuous Human Review

**Why custom interfaces?**: Off-the-shelf tools don't support domain-specific needs

#### HCI Principles for Review Interfaces

1. **Show relevant context** (full conversation, not just last turn)
2. **Enable rapid annotation** (keyboard shortcuts, bulk actions)
3. **Support comparison** (side-by-side A/B)
4. **Visualize patterns** (clustering, grouping)
5. **Integrate with workflow** (link to tickets, deploy from UI)

#### Sampling Strategies

**Which traces to review?**

1. **Random sampling**: Unbiased baseline
2. **Uncertainty sampling**: Eval scores near threshold (e.g., 0.4-0.6)
3. **Failure-driven**: Sample from eval failures
4. **Diversity**: Cluster embeddings, sample from each cluster
5. **Recency**: Prioritize recent production data

**Recommended**: Combine multiple strategies (e.g., 50% failures + 30% uncertain + 20% random)

#### Case Studies

**EvalGen** (Shankar et al.):
- Groups traces by similarity
- Shows representative examples from each group
- Enables pattern discovery

**DocWrangler** (Shankar et al.):
- Interactive prompt refinement
- Live preview of LLM behavior on data
- Tight feedback loop (edit prompt → see results immediately)

---

### Chapter 11: Improvement

#### Accuracy Optimization (Progression)

**Quick Wins** (hours):
- Add examples to prompt
- Clarify ambiguous instructions
- Fix obvious prompt errors

**Structural Changes** (days):
- Chain-of-thought prompting
- Task decomposition (break complex task into steps)
- Add retrieval (RAG)
- Implement tool calling

**Heavier Fixes** (weeks):
- Fine-tuning on domain data
- Ensemble methods
- Upgrade to better foundation model
- Redesign architecture

#### Cost Reduction Strategies

**1. Quick Wins**
- Use smaller models for simple subtasks
- Reduce output tokens (be specific about length)
- Batch API requests
- Remove unnecessary context

**2. Tiered Models**
- Route simple queries to small models
- Use large models only for complex queries
- Example: Classify query complexity first

**3. Prompt Optimization**
- Shorter prompts (remove redundant instructions)
- Fewer examples (test 1-shot vs 3-shot)
- Compression techniques

**4. Token-Level Optimization**
- Remove whitespace
- Use abbreviations (where unambiguous)
- Structured output formats (JSON more compact than prose)

#### LLM Provider Caching

**How it works**:
- Providers cache prompt prefixes
- Reuse KV cache for identical prefixes
- Dramatically reduces latency + cost

**Best Practices**:
- Put static content at beginning (system prompt, examples)
- Put dynamic content at end (user query)
- Align cache boundaries (typically 1024-token blocks)

**Example**:
```
[Static: System prompt + examples] ← Cached
[Dynamic: User query] ← Not cached
```

#### Advanced: Model Cascades

**Concept**: Try cheap model first, escalate to expensive model if needed

**Simple Cascade**:
```python
def cascade(query):
    cheap_response = small_model(query)
    if confidence(cheap_response) > threshold:
        return cheap_response
    else:
        return large_model(query)
```

**Confidence Estimation**:
- Use LLM-as-judge on cheap response
- Perplexity scores
- Self-consistency (sample multiple times, check agreement)

**Optimization**:
- Tune threshold on validation set
- Measure cost vs accuracy tradeoff

---

## Key Takeaways for Your Recipe Chatbot

Based on this course, here's how to apply to your 60-min workshop:

### Workshop Structure

**Part 1: Quick Evals (20 min)** → **Chapter 2-3 concepts**
- Load pre-collected traces
- Run LLM-as-judge eval (Chapter 5)
- Show mismatches
- Exercise: Tweak eval prompt

**Part 2: Failure Analysis (25 min)** → **Chapter 8 concepts + HW5**
- Multi-step pipeline (recipe agent states)
- Transition failure matrix
- Heat-map visualization
- Exercise: Identify top failure mode, hypothesize root cause

**Wrap-up (10 min)** → **Chapter 9-11 concepts**
- Show "what's next" (CI/CD, monitoring, improvement)

### Data You Already Have

- ✅ 100 labeled traces (HW5)
- ✅ Mismatches (HW3)
- ✅ Agent architecture (recipe chatbot)
- ✅ Failure taxonomy (annotation work)

### Code Patterns to Reuse

1. **LLM-as-Judge** (Chapter 5)
2. **Transition Matrix** (Chapter 8 + HW5)
3. **Heat-map Visualization** (Chapter 8 + HW5)

---

## Course Philosophy Summary

1. **Look at your data** - No substitute for manual inspection
2. **Start simple** - Binary evals before 1-5 scales
3. **Iterate** - Analyze → Measure → Improve is a loop
4. **Be skeptical** - Generic metrics are often useless
5. **Application-specific** - Foundation benchmarks don't predict your app's performance

**Most important quote**: "If you are not willing to look at some data manually on a regular cadence you are wasting your time with evals."
