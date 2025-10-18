#!/usr/bin/env python3
"""Clear all annotation data from DuckDB while preserving trace_runs and labelers."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import duckdb
except ModuleNotFoundError as exc:
    raise SystemExit(
        "DuckDB is required. Install with `pip install duckdb` or `uv pip install duckdb`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parent.parent
DUCKDB_PATH = REPO_ROOT / "data" / "email_annotations.duckdb"


def clear_annotations(db_path: Path, confirm: bool = False) -> None:
    """Clear all annotation data while preserving trace_runs and labelers.

    Deletes data from:
    - axial_links (all failure mode assignments)
    - annotations (all notes/observations)
    - email_judgments (all pass/fail judgments)
    - failure_modes (all failure mode definitions)

    Preserves:
    - trace_runs (run history)
    - labelers (annotator information)
    """
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = duckdb.connect(str(db_path))

    # Get counts before deletion
    axial_count = conn.execute("SELECT COUNT(*) FROM axial_links").fetchone()[0]
    annotation_count = conn.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]
    judgment_count = conn.execute("SELECT COUNT(*) FROM email_judgments").fetchone()[0]
    failure_mode_count = conn.execute("SELECT COUNT(*) FROM failure_modes").fetchone()[0]
    run_count = conn.execute("SELECT COUNT(*) FROM trace_runs").fetchone()[0]
    labeler_count = conn.execute("SELECT COUNT(*) FROM labelers").fetchone()[0]

    print("\n📊 Current Database Status:")
    print(f"  • Axial links: {axial_count:,}")
    print(f"  • Annotations: {annotation_count:,}")
    print(f"  • Judgments: {judgment_count:,}")
    print(f"  • Failure modes: {failure_mode_count:,}")
    print(f"  • Trace runs: {run_count:,} (will be preserved)")
    print(f"  • Labelers: {labeler_count:,} (will be preserved)")

    if not confirm:
        response = input("\n⚠️  This will delete ALL annotation data. Continue? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Aborted")
            conn.close()
            return

    print("\n🗑️  Clearing annotation data...")

    # Delete in order respecting foreign key constraints
    conn.execute("DELETE FROM axial_links")
    print(f"  ✓ Deleted {axial_count:,} axial links")

    conn.execute("DELETE FROM annotations")
    print(f"  ✓ Deleted {annotation_count:,} annotations")

    conn.execute("DELETE FROM email_judgments")
    print(f"  ✓ Deleted {judgment_count:,} judgments")

    conn.execute("DELETE FROM failure_modes")
    print(f"  ✓ Deleted {failure_mode_count:,} failure modes")

    conn.close()

    print(f"\n✅ Annotation data cleared successfully!")
    print(f"   Preserved {run_count:,} trace runs and {labeler_count:,} labelers")


def main():
    parser = argparse.ArgumentParser(
        description="Clear all annotation data while preserving trace_runs and labelers"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DUCKDB_PATH,
        help=f"Path to DuckDB file (default: {DUCKDB_PATH})",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()
    clear_annotations(args.db, confirm=args.yes)


if __name__ == "__main__":
    main()
