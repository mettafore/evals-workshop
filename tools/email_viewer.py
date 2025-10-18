"""Interactive email viewer for hand-picking tutorial samples.

Usage:
    python tools/email_viewer.py \
        --emails data/filtered_emails.csv \
        --output data/curated_emails.csv

Controls inside the viewer:
    Left / h   : previous email
    Right / l  : next email
    Up / Down  : scroll within the email body
    Enter      : toggle selection (adds/removes current email)
    b          : toggle between condensed and full body view
    s          : save current selections to output file
    g          : jump to a specific row index
    :<number>  : jump to index (vim-style command)
    q          : quit (auto-saves if --auto-save is enabled)

Selected emails are written to CSV with the same columns as the source file
plus an added column `selection_rank` indicating selection order.
"""

from __future__ import annotations

import argparse
import csv
import curses
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import pandas as pd

DISPLAY_COLUMNS = [
    "subject",
    "from_email",
    "to_emails",
    "date_raw",
]

BODY_COLUMN = "body"


@dataclass
class EmailRecord:
    index: int
    data: pd.Series


def load_emails(path: Path, limit: int | None = None) -> List[EmailRecord]:
    """Load email rows from CSV into EmailRecord list."""
    df = pd.read_csv(path)
    if limit is not None:
        df = df.head(limit)
    records = [EmailRecord(idx, row) for idx, row in df.iterrows()]
    return records


def wrap_text(text: str, width: int) -> List[str]:
    wrapper = textwrap.TextWrapper(width=width, replace_whitespace=False, drop_whitespace=False)
    lines = []
    for paragraph in text.splitlines():
        if not paragraph:
            lines.append("")
            continue
        lines.extend(wrapper.wrap(paragraph) or [""])
    return lines


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def draw_email(
    stdscr: curses.window,
    record: EmailRecord,
    selected_indices: Sequence[int],
    show_full_body: bool,
    scroll_offset: int,
    header_height: int = 7,
) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    title = "Email Selector · filtered_emails.csv"
    stdscr.addstr(0, 0, title[:width], curses.A_BOLD)

    meta_lines = [
        f"Index: {record.index}",
        f"Selected: {len(selected_indices)}",
        "",
    ]
    for col in DISPLAY_COLUMNS:
        value = record.data.get(col, "")
        if isinstance(value, float) and pd.isna(value):
            value = ""
        meta_lines.append(f"{col}: {value}")

    for offset, line in enumerate(meta_lines, start=1):
        if offset >= height:
            break
        stdscr.addstr(offset, 0, str(line)[:width])

    body_text = record.data.get(BODY_COLUMN, "") or ""
    available_height = height - header_height
    if available_height < 3:
        available_height = 3
    wrapped_body = wrap_text(body_text, width - 2)
    total_lines = len(wrapped_body)

    if show_full_body:
        max_scroll = max(total_lines - available_height, 0)
        offset = max(0, min(scroll_offset, max_scroll))
        display_lines = wrapped_body[offset : offset + available_height]
    else:
        if total_lines > available_height:
            display_lines = wrapped_body[: available_height - 1] + ["... (press 'b' for full body)"]
        else:
            display_lines = wrapped_body

    start_row = header_height
    for offset, line in enumerate(display_lines):
        row = start_row + offset
        if row >= height:
            break
        stdscr.addstr(row, 0, line[: width - 1])


    instructions = "Keys: Up/Down scroll | Left/Right navigate | Enter select | b body | s save | g goto | :number jump | q quit"
    stdscr.addstr(height - 1, 0, instructions[:width], curses.A_REVERSE)

    if record.index in selected_indices:
        stdscr.addstr(0, width - 18, "[SELECTED]", curses.A_BOLD)

    stdscr.refresh()


def prompt_goto(stdscr: curses.window, prompt: str) -> int | None:
    curses.echo()
    height, width = stdscr.getmaxyx()
    stdscr.addstr(height - 2, 0, " " * (width - 1))
    stdscr.addstr(height - 2, 0, prompt[: width - 1])
    stdscr.refresh()
    try:
        value = stdscr.getstr(height - 2, len(prompt), 8)
        if not value:
            return None
        return int(value.decode())
    except ValueError:
        return None
    finally:
        curses.noecho()


def save_selection(records: List[EmailRecord], selection_order: List[int], output_path: Path) -> None:
    if not selection_order:
        output_path.write_text("", encoding="utf-8")
        return

    df_rows = []
    lookup = {r.index: r for r in records}
    for rank, idx in enumerate(selection_order, start=1):
        rec = lookup[idx]
        row = rec.data.to_dict()
        row["selection_rank"] = rank
        df_rows.append(row)

    fieldnames = list(df_rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(df_rows)


def run_viewer(stdscr: curses.window, records: List[EmailRecord], output_path: Path, auto_save: bool) -> List[int]:
    curses.curs_set(0)
    current = 0
    show_full_body = True
    selected_order: List[int] = []
    scroll_offset = 0

    while records:
        current = clamp(current, 0, len(records) - 1)
        record = records[current]
        draw_email(stdscr, record, selected_order, show_full_body, scroll_offset)
        key = stdscr.getch()

        # Clamp scroll offset after drawing to avoid runaway values
        max_scroll = max(len(wrap_text(record.data.get(BODY_COLUMN, '') or '', stdscr.getmaxyx()[1] - 2)) - (stdscr.getmaxyx()[0] - 7), 0)
        scroll_offset = max(0, min(scroll_offset, max_scroll))

        if key in (ord("q"), 27):
            if auto_save:
                save_selection(records, selected_order, output_path)
            break
        elif key in (curses.KEY_RIGHT, ord("l")):
            current = min(current + 1, len(records) - 1)
            scroll_offset = 0
        elif key in (curses.KEY_LEFT, ord("h")):
            current = max(current - 1, 0)
            scroll_offset = 0
        elif key in (curses.KEY_DOWN, ord("j")):
            if not show_full_body:
                show_full_body = True
                scroll_offset = 0
            else:
                scroll_offset += 1
        elif key in (curses.KEY_UP, ord("k")):
            if not show_full_body:
                show_full_body = True
                scroll_offset = 0
            else:
                scroll_offset = max(scroll_offset - 1, 0)
        elif key in (10, 13):  # Enter key
            scroll_offset = 0
            idx = record.index
            if idx in selected_order:
                selected_order.remove(idx)
            else:
                selected_order.append(idx)
            current = min(current + 1, len(records) - 1)
        elif key == ord("b"):
            show_full_body = not show_full_body
            scroll_offset = 0
        elif key == ord("s"):
            save_selection(records, selected_order, output_path)
            status = f"Saved {len(selected_order)} records to {output_path}"[: stdscr.getmaxyx()[1] - 1]
            stdscr.addstr(1, 0, status, curses.A_BOLD)
            stdscr.refresh()
        elif key == ord(":"):
            target = prompt_goto(stdscr, ":")
            if target is not None:
                matches = [i for i, rec in enumerate(records) if rec.index >= target]
                if matches:
                    current = matches[0]
                    scroll_offset = 0
        elif key == ord("g"):
            target = prompt_goto(stdscr, "Jump to index: ")
            if target is not None:
                matches = [i for i, rec in enumerate(records) if rec.index >= target]
                if matches:
                    current = matches[0]
                    scroll_offset = 0
        else:
            # ignore unhandled keys
            pass

    return selected_order


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive filtered email selector")
    parser.add_argument("--emails", type=Path, default=Path("data/filtered_emails.csv"), help="CSV file with emails")
    parser.add_argument("--output", type=Path, default=Path("data/curated_emails.csv"), help="Where to write selected emails")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of emails to load")
    parser.add_argument("--auto-save", action="store_true", help="Automatically save on quit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_emails(args.emails, args.limit)
    if not records:
        raise SystemExit("No emails found in the provided CSV")

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    selected_order: List[int] = []

    def curses_app(stdscr: curses.window) -> None:
        nonlocal selected_order
        selected_order = run_viewer(stdscr, records, output_path, args.auto_save)

    curses.wrapper(curses_app)

    # Save once more after leaving the interface (unless already empty file created)
    save_selection(records, selected_order, output_path)
    print(f"Saved {len(selected_order)} selected emails to {output_path}")


if __name__ == "__main__":
    main()
