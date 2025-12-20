#!/usr/bin/env python3
"""
Curses Terminal Matcher (realtime top-K matches)

Usage:
  # Candidates from a file (one per line)
  python terminal_matcher_curses.py --file corpus.txt

  # Or pipe candidates via stdin
  cat corpus.txt | python terminal_matcher_curses.py

Controls:
  - Type to search
  - Backspace to delete
  - ESC or Ctrl+C to quit
  - Ctrl+U clears the whole query
"""

from __future__ import annotations

import argparse
import curses
import difflib
import sys
from typing import List, Tuple

TOP_K_DEFAULT = 10


# def load_corpus(file_path: str | None) -> List[str]:
#     if file_path:
#         with open(file_path, "r", encoding="utf-8", errors="replace") as f:
#             lines = [ln.rstrip("\n") for ln in f]
#     else:
#         # stdin must be piped for this to work
#         data = sys.stdin.read().splitlines()
#         lines = [ln for ln in data]

#     # remove empty-ish lines
#     return [ln.strip() for ln in lines if ln.strip()]


def load_corpus_from_files(paths: list[str]) -> list[str]:
    corpus = []
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    corpus.append(line)
    return corpus


def score_candidate(query: str, candidate: str) -> float:
    """
    Fast-ish scoring:
      - strong boost if query is substring
      - else difflib similarity ratio
    """
    q = query.strip().lower()
    c = candidate.strip().lower()
    if not q:
        return 0.0

    if q in c:
        idx = c.find(q)
        # base boost + earlier match slightly better
        return 2.0 + max(0.0, 1.0 - (idx / max(1, len(c))))

    return difflib.SequenceMatcher(a=q, b=c).ratio()


def top_k_matches(query: str, corpus: List[str], k: int) -> List[Tuple[float, str]]:
    if not query.strip():
        return []
    scored: List[Tuple[float, str]] = []
    for line in corpus:
        s = score_candidate(query, line)
        if s > 0:
            scored.append((s, line))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:k]


def draw(
    stdscr: "curses._CursesWindow",
    query: str,
    matches: List[Tuple[float, str]],
    k: int,
    corpus_size: int,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    header = f"Realtime Terminal Matcher | corpus: {corpus_size} | top: {k} | ESC/Ctrl+C quit | Ctrl+U clear"
    stdscr.addnstr(0, 0, header, w - 1)

    stdscr.addnstr(2, 0, "> " + query, w - 1)

    stdscr.addnstr(4, 0, f"Top {k} matches:", w - 1)

    if not query.strip():
        stdscr.addnstr(6, 0, "(type to search)", w - 1)
    elif not matches:
        stdscr.addnstr(6, 0, "(no matches)", w - 1)
    else:
        row = 6
        for i, (s, line) in enumerate(matches, start=1):
            if row >= h:
                break
            text = f"{i}. [{s:0.3f}] {line}"
            stdscr.addnstr(row, 0, text, w - 1)
            row += 1

    stdscr.refresh()


def main_curses(stdscr: "curses._CursesWindow", corpus: List[str], k: int) -> int:
    curses.curs_set(0)
    stdscr.keypad(True)

    query = ""
    matches: List[Tuple[float, str]] = []

    draw(stdscr, query, matches, k, len(corpus))

    while True:
        ch = stdscr.getch()

        # Ctrl+C
        if ch == 3:
            return 0

        # ESC
        if ch == 27:
            return 0

        # Ctrl+U clears query
        if ch == 21:
            query = ""
        # Backspace variants
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            query = query[:-1]
        # Ignore Enter
        elif ch in (10, 13):
            pass
        # Printable ASCII
        elif 32 <= ch <= 126:
            query += chr(ch)
        else:
            # ignore other control keys for now
            pass

        matches = top_k_matches(query, corpus, k)
        draw(stdscr, query, matches, k, len(corpus))


def main() -> int:
    parser = argparse.ArgumentParser(description="Curses-based realtime terminal matcher.")
    # parser.add_argument("--file", type=str, help="Corpus file path (one candidate per line).")
    parser.add_argument(
        "--files",
        nargs="+",
        help="One or more corpus files (each line is a candidate)."
    )
    parser.add_argument("--topk", type=int, default=TOP_K_DEFAULT, help="Number of matches to show.")
    args = parser.parse_args()

    if not args.files and sys.stdin.isatty():
        sys.stderr.write("Provide --files OR pipe stdin with corpus lines.\n")
        sys.stderr.write("Example: cat corpus.txt | python terminal_matcher_curses.py\n")
        return 2

    # corpus = load_corpus(args.file)
    # if not corpus:
    #     sys.stderr.write("Corpus is empty.\n")
    #     return 2

    if args.files:
        corpus = load_corpus_from_files(args.files)
    else:
        corpus = load_corpus_from_stdin()


    k = max(1, args.topk)

    # curses.wrapper handles init/cleanup safely
    curses.wrapper(lambda stdscr: main_curses(stdscr, corpus, k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
