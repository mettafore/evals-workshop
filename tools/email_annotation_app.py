#!/usr/bin/env python3
"""Flask annotation tool tailored for the email summariser workshop."""

from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import duckdb  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "DuckDB is required. Install with `pip install duckdb` or `uv pip install duckdb` before running the annotation app."
    ) from exc
from flask import Flask, jsonify, render_template, request

REPO_ROOT = Path(__file__).resolve().parent.parent
DUCKDB_PATH = REPO_ROOT / "data" / "email_annotations.duckdb"
SCHEMA_SQL_PATH = REPO_ROOT / "sql" / "annotation_schema.sql"
TRACE_ROOT = REPO_ROOT / "annotation" / "traces"

app = Flask(
    __name__,
    template_folder=str(REPO_ROOT / "annotation" / "templates"),
    static_folder=str(REPO_ROOT / "annotation" / "static"),
)


def get_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(DUCKDB_PATH))
    if SCHEMA_SQL_PATH.exists():
        conn.execute(SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
    return conn


def latest_run_id(conn: duckdb.DuckDBPyConnection) -> Optional[str]:
    result = conn.execute(
        "SELECT run_id FROM trace_runs ORDER BY generated_at DESC LIMIT 1"
    ).fetchone()
    return result[0] if result else None


def resolve_run_id(
    conn: duckdb.DuckDBPyConnection, run_id: Optional[str]
) -> Optional[str]:
    if run_id:
        exists = conn.execute(
            "SELECT 1 FROM trace_runs WHERE run_id = ? LIMIT 1", (run_id,)
        ).fetchone()
        if exists:
            return run_id
    return latest_run_id(conn)


def load_trace_file(run_id: str, email_hash: str) -> Optional[Dict[str, Any]]:
    """Load trace JSON file for a given run_id and email_hash."""
    trace_file = TRACE_ROOT / run_id / f"trace_{email_hash}.json"
    if not trace_file.exists():
        return None
    try:
        trace_data = json.loads(trace_file.read_text(encoding="utf-8"))
        return trace_data
    except (json.JSONDecodeError, IOError):
        return None


def load_email(run_id: str, email_hash: str) -> Optional[Dict[str, Any]]:
    """Load email data from trace JSON file."""
    trace_data = load_trace_file(run_id, email_hash)
    if not trace_data:
        return None

    metadata = trace_data.get("metadata", {}).get("extra", {})

    # Extract LLM output from response
    response_content = (
        trace_data.get("response", {}).get("messages", [{}])[0].get("content", "{}")
    )
    try:
        llm_output = json.loads(response_content)
        summary = llm_output.get("summary", "")
        commitments = llm_output.get("commitments", [])
    except json.JSONDecodeError:
        summary = ""
        commitments = []

    # Extract email body from request
    request_content = (
        trace_data.get("request", {}).get("messages", [{}])[0].get("content", "")
    )
    # Parse body from the prompt (it's between triple backticks)
    body_match = request_content.split("```")
    body = body_match[1].strip() if len(body_match) > 2 else ""

    # Extract subject from metadata
    subject = metadata.get("normalized_subject", "").title() or "(no subject)"

    return {
        "email_hash": email_hash,
        "subject": subject,
        "body": body,
        "metadata": metadata,
        "run_id": run_id,
        "summary": summary,
        "commitments": commitments,
    }


def list_emails(run_id: str) -> List[Dict[str, Any]]:
    """List all emails for a given run by scanning trace directory."""
    run_dir = TRACE_ROOT / run_id
    if not run_dir.exists():
        return []

    emails = []
    for trace_file in sorted(run_dir.glob("trace_*.json")):
        email_hash = trace_file.stem.replace("trace_", "")
        trace_data = load_trace_file(run_id, email_hash)
        if trace_data:
            metadata = trace_data.get("metadata", {}).get("extra", {})
            subject = metadata.get("normalized_subject", "").title() or "(no subject)"
            emails.append(
                {
                    "email_hash": email_hash,
                    "subject": subject,
                    "metadata": metadata,
                }
            )
    return emails


def get_annotations(
    conn: duckdb.DuckDBPyConnection, email_hash: str
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT annotation_id, labeler_id, open_code, pass_fail, run_id, created_at
        FROM annotations
        WHERE email_hash = ?
        ORDER BY created_at DESC
        """,
        (email_hash,),
    ).fetchall()
    annotations = []
    for anno_id, labeler_id, open_code, pass_fail, run_id, created_at in rows:
        annotations.append(
            {
                "annotation_id": anno_id,
                "labeler_id": labeler_id,
                "open_code": open_code,
                "pass_fail": bool(pass_fail) if pass_fail is not None else None,
                "run_id": run_id,
                "created_at": created_at,
            }
        )
    return annotations


def get_failure_modes(conn: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT failure_mode_id, slug, display_name, definition
        FROM failure_modes
        ORDER BY display_name
        """
    ).fetchall()
    return [
        {
            "failure_mode_id": fm_id,
            "slug": slug,
            "display_name": display_name,
            "definition": definition,
        }
        for fm_id, slug, display_name, definition in rows
    ]


def get_selected_failure_modes(
    conn: duckdb.DuckDBPyConnection, email_hash: str
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT al.failure_mode_id, fm.display_name, fm.definition, al.annotation_id
        FROM axial_links al
        JOIN failure_modes fm ON al.failure_mode_id = fm.failure_mode_id
        WHERE al.annotation_id IN (SELECT annotation_id FROM annotations WHERE email_hash = ?)
        ORDER BY al.linked_at DESC
        """,
        (email_hash,),
    ).fetchall()
    return [
        {
            "failure_mode_id": failure_mode_id,
            "display_name": display_name,
            "definition": definition,
            "annotation_id": annotation_id,
        }
        for failure_mode_id, display_name, definition, annotation_id in rows
    ]


@app.route("/")
def index() -> str:
    return render_template("email_annotate.html")


@app.get("/api/context")
def api_context():
    with get_conn() as conn:
        run_id = resolve_run_id(conn, request.args.get("run_id"))
        if not run_id:
            return jsonify({"error": "No trace runs loaded yet"}), 400
        emails = list_emails(run_id)
        return jsonify(
            {
                "run_id": run_id,
                "email_hashes": [e["email_hash"] for e in emails],
                "emails": emails,
                "labelers": conn.execute(
                    "SELECT labeler_id, name FROM labelers ORDER BY created_at"
                ).fetchall(),
            }
        )


@app.get("/api/email/<email_hash>")
def api_email(email_hash: str):
    with get_conn() as conn:
        # Get run_id from query param or use latest
        run_id = resolve_run_id(conn, request.args.get("run_id"))
        if not run_id:
            return jsonify({"error": "No trace runs available"}), 400

        email = load_email(run_id, email_hash)
        if not email:
            return jsonify({"error": "Email not found"}), 404
        annotations = get_annotations(conn, email_hash)
        failure_modes = get_selected_failure_modes(conn, email_hash)
        return jsonify(
            {
                "email": email,
                "annotations": annotations,
                "failure_modes": failure_modes,
                "available_failure_modes": get_failure_modes(conn),
            }
        )


@app.post("/api/labelers")
def api_labelers_create():
    payload = request.json or {}
    labeler_id = payload.get("labeler_id") or uuid.uuid4().hex[:8]
    name = payload.get("name") or labeler_id
    email = payload.get("email")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO labelers(labeler_id, name, email) VALUES (?, ?, ?)",
            (labeler_id, name, email),
        )
    return jsonify({"labeler_id": labeler_id, "name": name, "email": email})


@app.post("/api/annotations")
def api_annotations_create():
    payload = request.json or {}
    email_hash_value = payload.get("email_hash")
    open_code = payload.get("open_code", "").strip()
    pass_fail = payload.get("pass_fail")
    labeler_id = payload.get("labeler_id")
    if not email_hash_value or not open_code:
        return jsonify({"error": "email_hash and open_code are required"}), 400
    annotation_id = uuid.uuid4().hex
    created_at = datetime.utcnow().isoformat() + "Z"
    with get_conn() as conn:
        run_id = resolve_run_id(conn, request.args.get("run_id"))
        if not run_id:
            return jsonify({"error": "No trace runs available"}), 400

        email = load_email(run_id, email_hash_value)
        if not email:
            return jsonify({"error": "Email not found"}), 404
        if labeler_id:
            exists = conn.execute(
                "SELECT 1 FROM labelers WHERE labeler_id = ? LIMIT 1", (labeler_id,)
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO labelers(labeler_id, name) VALUES (?, ?)",
                    (labeler_id, labeler_id),
                )
        conn.execute(
            """
            INSERT OR REPLACE INTO annotations(annotation_id, email_hash, labeler_id, open_code, pass_fail, run_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                annotation_id,
                email_hash_value,
                labeler_id,
                open_code,
                bool(pass_fail) if pass_fail is not None else None,
                email["run_id"],
                created_at,
                created_at,
            ),
        )
    return jsonify(
        {
            "annotation_id": annotation_id,
            "email_hash": email_hash_value,
            "labeler_id": labeler_id,
            "open_code": open_code,
            "pass_fail": pass_fail,
            "created_at": created_at,
        }
    )


@app.delete("/api/annotations/<annotation_id>")
def api_annotations_delete(annotation_id: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM axial_links WHERE annotation_id = ?", (annotation_id,)
        )
        conn.execute(
            "DELETE FROM annotations WHERE annotation_id = ?", (annotation_id,)
        )
    return jsonify({"deleted": annotation_id})


@app.post("/api/failure-modes")
def api_failure_modes_create():
    payload = request.json or {}
    display_name = payload.get("display_name", "New Failure Mode").strip()
    slug = payload.get("slug") or display_name.lower().replace(" ", "-")
    definition = payload.get("definition", "")
    failure_mode_id = payload.get("failure_mode_id") or uuid.uuid4().hex[:8]
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO failure_modes(failure_mode_id, slug, display_name, definition)
            VALUES (?, ?, ?, ?)
            """,
            (failure_mode_id, slug, display_name, definition),
        )
    return jsonify(
        {
            "failure_mode_id": failure_mode_id,
            "slug": slug,
            "display_name": display_name,
            "definition": definition,
        }
    )


@app.post("/api/axial-links")
def api_axial_links_create():
    payload = request.json or {}
    annotation_id = payload.get("annotation_id")
    failure_mode_id = payload.get("failure_mode_id")
    if not annotation_id or not failure_mode_id:
        return jsonify({"error": "annotation_id and failure_mode_id are required"}), 400
    with get_conn() as conn:
        annotation = conn.execute(
            "SELECT run_id FROM annotations WHERE annotation_id = ?",
            (annotation_id,),
        ).fetchone()
        if not annotation:
            return jsonify({"error": "Annotation not found"}), 404
        conn.execute(
            """
            INSERT OR REPLACE INTO axial_links(annotation_id, failure_mode_id, run_id)
            VALUES (?, ?, ?)
            """,
            (annotation_id, failure_mode_id, annotation[0]),
        )
    return jsonify({"annotation_id": annotation_id, "failure_mode_id": failure_mode_id})


@app.delete("/api/axial-links")
def api_axial_links_delete():
    annotation_id = request.args.get("annotation_id")
    failure_mode_id = request.args.get("failure_mode_id")
    if not annotation_id or not failure_mode_id:
        return jsonify({"error": "annotation_id and failure_mode_id required"}), 400
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM axial_links WHERE annotation_id = ? AND failure_mode_id = ?",
            (annotation_id, failure_mode_id),
        )
    return jsonify({"removed": True})


@app.get("/api/failure-modes/suggest")
def api_failure_modes_suggest():
    email_hash = request.args.get("email_hash")
    if not email_hash:
        return jsonify({"error": "email_hash required"}), 400
    with get_conn() as conn:
        annotations = get_annotations(conn, email_hash)
    word_counter: Counter[str] = Counter()
    for ann in annotations:
        tokens = re.findall(r"[A-Za-z]{4,}", ann["open_code"].lower())
        word_counter.update(tokens)
    suggestions = [
        {
            "display_name": word.title(),
            "definition": f"Auto-suggested from frequent token '{word}'",
            "slug": word,
        }
        for word, _ in word_counter.most_common(5)
    ]
    return jsonify({"suggestions": suggestions})


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
