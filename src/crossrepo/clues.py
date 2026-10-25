"""Clue writing: every answer gets a clue derived from real code facts."""

from __future__ import annotations

import random

from .scan import RepoFacts
from .words import Word

_MAX_DOC = 90


def make_clues(words: list[Word], facts: RepoFacts, rng: random.Random) -> dict[str, str]:
    """Map each answer to a clue. Same words + same rng -> same clues."""
    return {w.text: _clue_for(w, facts, rng) for w in words}


def _shorten(doc: str) -> str:
    doc = doc.strip()
    if len(doc) > _MAX_DOC:
        doc = doc[: _MAX_DOC - 3].rstrip() + "..."
    return doc


def _clue_for(word: Word, facts: RepoFacts, rng: random.Random) -> str:
    if word.is_fragment:
        # Deliberately shows the parent identifier: a hidden-word hint.
        return f"Part of the identifier '{word.parent}' in {word.symbol.file}"
    sym = word.symbol
    if sym.kind == "repo":
        return "The name of this very repository"
    doc = _shorten(sym.docstring)
    candidates: list[str] = []
    if sym.kind == "class":
        candidates.append(f"A class defined in {sym.file}")
        if doc:
            candidates.append(f"Class described as '{doc}' (in {sym.file})")
    elif sym.kind in ("function", "method"):
        kind = "method" if sym.kind == "method" else "function"
        candidates.append(f"A {kind} defined in {sym.file}")
        if doc:
            candidates.append(f"A {kind} whose docstring begins: '{doc}'")
    elif sym.kind == "module":
        candidates.append("One of this repository's source modules")
        candidates.append(f"Find it somewhere under {facts.name}/")
    elif sym.kind == "constant":
        candidates.append(f"An ALL-CAPS constant declared in {sym.file}")
    elif sym.kind == "identifier":
        candidates.append(f"An identifier that shows up ~{sym.refs} times in this repo")
    if sym.kind in ("class", "function", "method") and sym.refs >= 3:
        candidates.append(f"Referenced {sym.refs} times across this repository")
    candidates.append(
        f"An identifier from this repo: {len(word.text)} letters, starting with '{word.text[0]}'"
    )
    # Never leak the answer inside its own clue (file paths can give it away).
    safe = [c for c in candidates if word.text.lower() not in c.lower()]
    return rng.choice(safe or candidates)
