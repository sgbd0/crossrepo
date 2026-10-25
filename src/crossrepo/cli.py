"""Command line interface: ``crossrepo`` or ``python -m crossrepo``."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from . import __version__
from .clues import make_clues
from .layout import build as build_layout
from .render import render_html, render_json, render_text
from .scan import harvest
from .words import build_words


def _tame_console() -> None:
    """Never crash or garble on consoles that cannot encode clue text."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _tame_console()
    parser = argparse.ArgumentParser(
        prog="crossrepo",
        description="Turn a codebase into a crossword puzzle whose clues come from your own code.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("root", nargs="?", default=".",
                        help="repository path to scan (default: current directory)")
    parser.add_argument("--words", type=int, default=24, metavar="N",
                        help="how many candidate identifiers to mine (default: 24)")
    parser.add_argument("--seed", type=int, default=0,
                        help="seed for a reproducible puzzle (default: 0)")
    parser.add_argument("--reveal", action="store_true",
                        help="print the filled grid instead of the blank one")
    parser.add_argument("--stats", action="store_true",
                        help="only print repository statistics")
    parser.add_argument("--title", default=None,
                        help="puzzle title (default: '<repo name> - a crossword')")
    parser.add_argument("--txt", metavar="PATH",
                        help="write the text puzzle to a file instead of stdout")
    parser.add_argument("--html", metavar="PATH",
                        help="also write a standalone interactive HTML puzzle")
    parser.add_argument("--json", dest="json_path", metavar="PATH",
                        help="also write a JSON export")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"crossrepo: not a directory: {root}", file=sys.stderr)
        return 2

    facts = harvest(root)
    if args.stats:
        print(f"repository : {facts.name}")
        print(f"mode       : {facts.mode}")
        print(f"code files : {facts.total_files}")
        print(f"lines      : {facts.total_loc}")
        print(f"symbols    : {len(facts.symbols)}")
        return 0

    words = build_words(facts, limit=max(args.words, 8))
    if len(words) < 4:
        print("crossrepo: fewer than 4 usable identifiers found; nothing to puzzle over.",
              file=sys.stderr)
        return 2

    clue_rng = random.Random((args.seed * 1_000_003) ^ 0x5EED)
    clues = make_clues(words, facts, clue_rng)
    layout = build_layout([w.text for w in words], seed=args.seed)
    if layout is None or len(layout.placements) < 4:
        print("crossrepo: could not weave a crossword from these identifiers; try --words 40.",
              file=sys.stderr)
        return 2

    title = args.title or f"{facts.name} - a crossword"
    meta = {"files": facts.total_files, "loc": facts.total_loc,
            "symbols": len(facts.symbols), "mode": facts.mode}

    text = render_text(layout, clues, title=title, reveal=args.reveal)
    if args.txt:
        Path(args.txt).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.txt}")
    else:
        print(text)
    if args.html:
        Path(args.html).write_text(
            render_html(layout, clues, title=title, seed=args.seed), encoding="utf-8")
        print(f"wrote {args.html}")
    if args.json_path:
        payload = render_json(layout, clues, title=title, seed=args.seed, meta=meta)
        Path(args.json_path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {args.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
