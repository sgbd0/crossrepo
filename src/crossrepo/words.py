"""Word candidate mining: repository identifiers -> crossword answers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .scan import RepoFacts, Symbol

MIN_LEN = 3
MAX_LEN = 15
STOPWORDS = {
    "THE", "AND", "NOT", "FOR", "WITH", "FROM", "THIS", "THAT",
    "SELF", "NONE", "TRUE", "FALSE", "INIT", "ARGS", "KWARGS",
}
KIND_PRIORITY = {
    "repo": 6, "class": 5, "function": 4, "module": 4,
    "method": 3, "constant": 2, "identifier": 1,
}


@dataclass
class Word:
    """A crossword answer plus the symbol it came from."""

    text: str  # normalized: uppercase, letters only
    symbol: Symbol
    is_fragment: bool = False
    parent: str = ""


def normalize(name: str) -> str:
    """Strip digits and underscores so any identifier can live on a grid."""
    return re.sub(r"[^A-Za-z]", "", name).upper()


def split_identifier(name: str) -> list[str]:
    """Split snake_case and camelCase identifiers into their parts."""
    parts: list[str] = []
    for chunk in name.split("_"):
        parts.extend(re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z0-9]+|[A-Z]+", chunk))
    return parts


def _score(word: Word) -> tuple[int, int, int]:
    sym = word.symbol
    return (KIND_PRIORITY.get(sym.kind, 0), min(sym.refs, 500), len(word.text))


def build_words(facts: RepoFacts, limit: int = 24, fragment_cap: int = 4) -> list[Word]:
    """Pick the most crossword-worthy identifiers found in *facts*.

    Ranks real symbols first (classes and well-referenced functions win),
    adds the repository name, then a few identifier fragments (the
    ``LAYOUT`` inside ``layout_engine``) to help the grid interlock.
    """
    best: dict[str, Word] = {}
    for sym in facts.symbols:
        if sym.name.startswith("_"):
            continue
        text = normalize(sym.name)
        if not (MIN_LEN <= len(text) <= MAX_LEN) or not text.isalpha() or text in STOPWORDS:
            continue
        candidate = Word(text, sym)
        previous = best.get(text)
        if previous is None or _score(candidate) > _score(previous):
            best[text] = candidate
    ranked = sorted(best.values(), key=_score, reverse=True)
    words = ranked[:limit]

    repo_name = normalize(facts.name)
    if (MIN_LEN <= len(repo_name) <= MAX_LEN and repo_name.isalpha()
            and repo_name not in STOPWORDS and repo_name not in {w.text for w in words}):
        words.append(Word(repo_name, Symbol(facts.name, "repo", refs=10**6)))

    seen = {w.text for w in words}
    fragments: list[Word] = []
    for word in ranked[:12]:
        for part in split_identifier(word.symbol.name):
            frag = normalize(part)
            if (4 <= len(frag) <= MAX_LEN and frag.isalpha()
                    and frag not in STOPWORDS and frag not in seen):
                seen.add(frag)
                fragments.append(Word(frag, word.symbol, is_fragment=True, parent=word.symbol.name))
    return words + fragments[:fragment_cap]
