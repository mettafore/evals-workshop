#!/usr/bin/env python3
"""Generate synthetic LLM-judge coherence dataset entries via an LLM call.

This script reads an instruction prompt (default: prompts/llm_judge_synthetic_demo.txt),
invokes the configured LLM through pydantic-ai, and writes the structured dataset
returned by the model as JSON.

Example:
    uv run python tools/generate_synthetic.py \
        --prompt prompts/llm_judge_synthetic_demo.txt \
        --output data/llm-judge-sample-4.json \
        --model openai:gpt-5 \
        --email-id 075

Environment:
    PYDANTIC_AI_MODEL may be set to override the default model.
    Ensure your provider credentials (e.g., OPENAI_API_KEY) are configured.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

try:
    from pydantic_ai import Agent  # type: ignore
    from pydantic_ai.exceptions import UnexpectedModelBehavior  # type: ignore
except ModuleNotFoundError as exc:
    raise SystemExit(
        "pydantic-ai is required. Install with `pip install pydantic-ai`."
    ) from exc


class CoherenceExample(BaseModel):
    email_id: str = Field(..., description="Unique identifier for the synthetic email")
    email: str = Field(..., description="Full business email text (150-250 words)")
    summary: str = Field(..., description="Summary corresponding to the email")
    human_judgement: Literal["PASS", "FAIL"]
    human_reasoning: str = Field(..., description="Explanation of the judgement focusing on coherence")


class DatasetPayload(BaseModel):
    examples: List[CoherenceExample] = Field(..., min_items=1)


@dataclass
class GenerationResult:
    payload: DatasetPayload
    model: str
    prompt_path: Path


def default_model() -> str:
    env_model = os.getenv("PYDANTIC_AI_MODEL")
    if env_model:
        return env_model
    return "openai:gpt-4o-mini"


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Prompt file not found at {path}")
    return path.read_text(encoding="utf-8")


def build_job_prompt(prompt_text: str) -> str:
    enforcement = (
        "\n\n---\n"
        "Return JSON that matches this schema exactly:\n"
        "{\n"
        "  \"examples\": [\n"
        "    {\n"
        "      \"email_id\": string,\n"
        "      \"email\": string,\n"
        "      \"summary\": string,\n"
        "      \"human_judgement\": \"PASS\" or \"FAIL\",\n"
        "      \"human_reasoning\": string\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Ensure the JSON can be parsed without modification."
    )
    return prompt_text.rstrip() + enforcement


def run_generation(prompt_path: Path, model_name: str) -> GenerationResult:
    prompt_text = load_prompt(prompt_path)
    job_prompt = build_job_prompt(prompt_text)

    agent = Agent(model_name, system_prompt="")

    try:
        result = agent.run_sync(job_prompt, output_type=DatasetPayload)
    except UnexpectedModelBehavior as exc:
        raise SystemExit(
            "LLM response deviated from the expected schema. Adjust the prompt or model and retry."
        ) from exc

    return GenerationResult(payload=result.output, model=model_name, prompt_path=prompt_path)


def enforce_distribution(dataset: DatasetPayload, *, strict: bool = True) -> None:
    total = len(dataset.examples)
    fail = sum(example.human_judgement == "FAIL" for example in dataset.examples)
    pass_count = total - fail

    if strict:
        if total != 25:
            raise SystemExit(f"Expected 25 examples, received {total} instead.")
        if fail != 15 or pass_count != 10:
            raise SystemExit(
                f"Expected 15 FAIL and 10 PASS examples (60/40 split). Got FAIL={fail}, PASS={pass_count}."
            )


def apply_email_ids(dataset: DatasetPayload, base_id: str) -> None:
    match = re.match(r"^(.*?)(\d+)$", base_id)
    if not match:
        raise SystemExit("--email-id must end with digits (e.g., DEMO001)")
    prefix, digits = match.groups()
    width = len(digits)
    start = int(digits)

    for offset, example in enumerate(dataset.examples):
        seq = str(start + offset).zfill(width)
        example.email_id = f"{prefix}{seq}"


def serialize_dataset(dataset: DatasetPayload) -> str:
    return json.dumps({"examples": [example.model_dump() for example in dataset.examples]}, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic coherence dataset via LLM")
    parser.add_argument(
        "--prompt",
        type=Path,
        default=Path("prompts/llm_judge_synthetic_demo.txt"),
        help="Instruction prompt guiding the generation",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/llm_judge_synthetic_dataset.json"),
        help="Path to write the generated dataset (JSON)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=default_model(),
        help="LLM model identifier (overrides PYDANTIC_AI_MODEL)",
    )
    parser.add_argument(
        "--allow-mismatch",
        action="store_true",
        help="Do not abort if PASS/FAIL distribution differs from 60/40",
    )
    parser.add_argument(
        "--email-id",
        type=str,
        default="SYN001",
        help="Starting email_id (must end in digits; subsequent IDs increment)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_generation(args.prompt, args.model)

    apply_email_ids(result.payload, args.email_id)

    enforce_distribution(result.payload, strict=not args.allow_mismatch)

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_dataset(result.payload), encoding="utf-8")

    total = len(result.payload.examples)
    fail = sum(example.human_judgement == "FAIL" for example in result.payload.examples)
    print(
        f"Wrote {total} examples to {output_path} (FAIL={fail}, PASS={total - fail}) using model {result.model}."
    )


if __name__ == "__main__":
    main()
