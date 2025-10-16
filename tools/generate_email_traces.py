#!/usr/bin/env python3

"""Generate LLM-produced trace files and seed DuckDB tables for the workshop.

Key behaviours:
- Uses the short Git SHA as `run_id` (dirty worktrees are rejected).
- Calls the configured LLM through Pydantic AI with a structured `SummaryPayload` schema.
- Requires the `email_hash` column (written by Notebook 00) for stable identifiers.
- Supports optional parallel LLM calls via `--workers` threads.
- Writes traces under `annotation/traces/<run_id>/` along with copies of the prompt and source CSV.
- Upserts run/email metadata into `data/email_annotations.duckdb` for Notebook 02 analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from typing import Iterable, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from a .env file if present

try:
    import duckdb  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - surfaced at runtime
    raise SystemExit(
        "DuckDB is required. Install with `pip install duckdb` or `uv pip install duckdb`."
    ) from exc

try:
    from pydantic_ai import Agent  # type: ignore
    from pydantic_ai.exceptions import UnexpectedModelBehavior  # type: ignore
    from pydantic import BaseModel, Field
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "pydantic-ai is required. Install with `pip install pydantic-ai` and configure your provider credentials before generating traces."
    ) from exc

import pandas as pd

# Repository-relative paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EMAIL_PATH = REPO_ROOT / "data" / "filtered_emails.csv"
TRACE_ROOT = REPO_ROOT / "annotation" / "traces"
DEFAULT_PROMPT_PATH = REPO_ROOT / "prompts" / "email_summary_prompt.txt"
SCHEMA_SQL_PATH = REPO_ROOT / "sql" / "annotation_schema.sql"
DUCKDB_PATH = REPO_ROOT / "data" / "email_annotations.duckdb"


@dataclass
class TraceArtifacts:
    run_id: str
    prompt_template: str
    prompt_checksum: str
    prompt_path: Path
    source_csv: Path
    output_dir: Path
    model_name: str


@dataclass
class EmailJob:
    email_hash: str
    subject: str
    body: str
    metadata: dict


class SummaryPayload(BaseModel):
    summary: str = Field(..., description="Concise email summary")
    commitments: List[str] = Field(
        default_factory=list, description="Explicit commitments or action items"
    )


def git_short_sha() -> str:
    """Return the short git SHA (with -dirty suffix if needed)."""
    try:
        short_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=REPO_ROOT, text=True
        ).strip()
        if status:
            raise SystemExit(
                "Working tree has uncommitted changes. Commit or stash before generating traces."
            )
        return short_sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        return datetime.utcnow().strftime("run-%Y%m%d%H%M%S")


def load_prompt(path: Path) -> Tuple[str, str]:
    if not path.exists():
        raise SystemExit(
            f"Prompt file not found at {path}. Run Notebook 01 or specify --prompt before generating traces."
        )
    prompt_template = path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(prompt_template.encode("utf-8")).hexdigest()
    return prompt_template, checksum


def ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    if not SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"Missing schema SQL at {SCHEMA_SQL_PATH}")
    conn.execute(Path(SCHEMA_SQL_PATH).read_text(encoding="utf-8"))


def format_prompt_path(path: Path) -> str:
    if path.exists():
        try:
            return str(path.relative_to(REPO_ROOT))
        except ValueError:
            return str(path.resolve())
    return str(path)


def ingest_trace_run(
    conn: duckdb.DuckDBPyConnection, artifacts: TraceArtifacts
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO trace_runs(run_id, prompt_path, prompt_checksum, source_csv, model_name)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            artifacts.run_id,
            format_prompt_path(artifacts.prompt_path),
            artifacts.prompt_checksum,
            str(artifacts.source_csv.relative_to(REPO_ROOT)),
            artifacts.model_name,
        ),
    )


def record_email(
    conn: duckdb.DuckDBPyConnection,
    artifacts: TraceArtifacts,
    email_hash: str,
    subject: str,
    body: str,
    metadata: dict,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO emails_raw(email_hash, subject, body, metadata, run_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            email_hash,
            subject,
            body,
            json.dumps(metadata, ensure_ascii=False),
            artifacts.run_id,
        ),
    )


def _fmt(value: object, default: str = "Unknown") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def render_prompt(template: str, subject: str, body: str, metadata: dict) -> str:
    sender = _fmt(metadata.get("from_email") or metadata.get("from_raw"))
    to_line = _fmt(
        metadata.get("to_emails") or metadata.get("to_raw"),
        default="(no direct recipients recorded)",
    )
    cc_line = _fmt(
        metadata.get("cc_emails") or metadata.get("cc_raw"),
        default="(no cc recipients recorded)",
    )
    context = {
        "subject": subject or "No subject",
        "from_line": sender,
        "to_line": to_line,
        "cc_line": cc_line,
        "body": body,
    }
    return template.format(**context)


def call_llm_summary(
    artifacts: TraceArtifacts,
    subject: str,
    body: str,
    metadata: dict,
) -> Tuple[str, List[str], str]:
    job_prompt = render_prompt(artifacts.prompt_template, subject, body, metadata)

    try:
        result = Agent(
            artifacts.model_name,
            system_prompt="",
        ).run_sync(job_prompt, output_type=SummaryPayload)
    except UnexpectedModelBehavior as exc:
        raise RuntimeError(
            "LLM response did not conform to the expected schema. Review the prompt or model configuration."
        ) from exc

    payload: SummaryPayload = result.output

    commitments_text = [item.strip() for item in payload.commitments if item.strip()]
    return payload.summary.strip(), commitments_text, job_prompt


def create_trace_json(
    artifacts: TraceArtifacts,
    email_hash: str,
    subject: str,
    body: str,
    summary: str,
    commitments: List[str],
    metadata: dict,
    prompt_text: str,
) -> dict:
    timestamp = datetime.now(datetime.timezone.utc).isoformat() + "Z"
    return {
        "metadata": {
            "email_hash": email_hash,
            "run_id": artifacts.run_id,
            "generated_at": timestamp,
            "prompt_checksum": artifacts.prompt_checksum,
            "prompt_path": format_prompt_path(artifacts.prompt_path),
            "source_csv": str(artifacts.source_csv.relative_to(REPO_ROOT)),
            "model_name": artifacts.model_name,
            "extra": metadata,
        },
        "request": {
            "messages": [
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ]
        },
        "response": {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "summary": summary,
                            "commitments": commitments,
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        },
    }


def process_csv(
    dataframe: pd.DataFrame,
    artifacts: TraceArtifacts,
    limit: int | None,
    workers: int,
) -> List[Path]:
    output_files: List[Path] = []
    with duckdb.connect(str(DUCKDB_PATH)) as conn:
        ensure_schema(conn)
        ingest_trace_run(conn, artifacts)

        selected = dataframe.head(limit) if limit else dataframe

        jobs: List[EmailJob] = []
        for _, row in selected.iterrows():
            subject = str(row.get("subject", "")).strip()
            body = str(row.get("body", "")).strip()
            if not body:
                continue
            email_hash = str(row.get("email_hash", "")).strip()
            if not email_hash:
                raise RuntimeError(
                    "Missing `email_hash` column. Run Notebook 00 to populate hashes before generating traces."
                )
            metadata = {
                column: row[column]
                for column in row.index
                if column not in {"body", "subject"} and not pd.isna(row[column])
            }
            jobs.append(
                EmailJob(
                    email_hash=email_hash, subject=subject, body=body, metadata=metadata
                )
            )

        if not jobs:
            return output_files

        def summarize(job: EmailJob):
            summary, commitments, prompt_text = call_llm_summary(
                artifacts,
                job.subject,
                job.body,
                job.metadata,
            )
            return job, summary, commitments, prompt_text

        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(tqdm(pool.map(summarize, jobs), total=len(jobs), desc="Summarizing"))
        else:
            results = [summarize(job) for job in tqdm(jobs, desc="Summarizing", total=len(jobs))]

        for job, summary, commitments, prompt_text in results:
            record_email(
                conn, artifacts, job.email_hash, job.subject, job.body, job.metadata
            )

            trace_payload = create_trace_json(
                artifacts,
                job.email_hash,
                job.subject,
                job.body,
                summary,
                commitments,
                job.metadata,
                prompt_text,
            )
            out_path = artifacts.output_dir / f"trace_{job.email_hash}.json"
            out_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2))
            output_files.append(out_path)
    return output_files


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate trace JSON for workshop notebooks"
    )
    parser.add_argument(
        "--emails",
        type=Path,
        default=DEFAULT_EMAIL_PATH,
        help="Path to the email CSV source",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=TRACE_ROOT,
        help="Directory where traces will be written",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of emails to process",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("PYDANTIC_AI_MODEL"),
        help="Model identifier understood by pydantic-ai (default: env PYDANTIC_AI_MODEL or openai:gpt-4o-mini)",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=DEFAULT_PROMPT_PATH,
        help="Path to the prompt template (default: prompts/email_summary_prompt.txt)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel threads for LLM calls (default: 1)",
    )
    args = parser.parse_args(argv)

    if not args.emails.exists():
        raise FileNotFoundError(f"Email CSV not found at {args.emails}")

    run_id = git_short_sha()
    prompt_path = args.prompt.expanduser()
    prompt_template, prompt_checksum = load_prompt(prompt_path)

    output_dir = args.out / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.emails)

    artifacts = TraceArtifacts(
        run_id=run_id,
        prompt_template=prompt_template,
        prompt_checksum=prompt_checksum,
        prompt_path=prompt_path.resolve(),
        source_csv=args.emails.resolve(),
        output_dir=output_dir,
        model_name=args.model,
    )

    written = process_csv(df, artifacts, args.limit, max(1, args.workers))

    prompt_copy_path = artifacts.output_dir / "prompt.txt"
    prompt_copy_path.write_text(artifacts.prompt_template, encoding="utf-8")

    source_copy_path = artifacts.output_dir / "source.csv"
    shutil.copyfile(args.emails, source_copy_path)

    print(f"Generated {len(written)} traces in {output_dir}")
    print(f"Run ID: {artifacts.run_id}")
    print(f"DuckDB catalog: {DUCKDB_PATH}")


if __name__ == "__main__":
    main()
