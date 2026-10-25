"""Crossword layout engine.

Words are placed one by one, each crossing at least one letter of an
already placed word. A single invariant keeps every grid honest:

    every maximal horizontal/vertical run of 2+ letters must be a
    word that was deliberately placed.

That one rule rejects accidental merges (CAR + ARTS forming CART),
parallel touches, and any other nonsense adjacency.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

ACROSS = "across"
DOWN = "down"


@dataclass
class Placement:
    word: str
    row: int
    col: int
    direction: str
    number: int = 0


@dataclass
class Layout:
    cells: dict[tuple[int, int], str] = field(default_factory=dict)
    placements: list[Placement] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)

    @property
    def rows(self) -> int:
        return max((r for (r, _c) in self.cells), default=-1) + 1

    @property
    def cols(self) -> int:
        return max((c for (_r, c) in self.cells), default=-1) + 1


def _runs_with_cells(cells: dict[tuple[int, int], str]):
    """Every maximal horizontal/vertical run of 2+ letters, with its cells."""
    found: list[tuple[str, list[tuple[int, int]]]] = []
    by_row: dict[int, list[int]] = {}
    by_col: dict[int, list[int]] = {}
    for (r, c) in cells:
        by_row.setdefault(r, []).append(c)
        by_col.setdefault(c, []).append(r)
    for index_map, axis in ((by_row, 0), (by_col, 1)):
        for fixed, positions in index_map.items():
            streak: list[tuple[int, int]] = []
            previous = None
            for pos in sorted(positions):
                cell = (fixed, pos) if axis == 0 else (pos, fixed)
                if previous is not None and pos == previous + 1:
                    streak.append(cell)
                else:
                    if len(streak) >= 2:
                        found.append(("".join(cells[c] for c in streak), streak))
                    streak = [cell]
                previous = pos
            if len(streak) >= 2:
                found.append(("".join(cells[c] for c in streak), streak))
    return found


def runs(cells: dict[tuple[int, int], str]) -> list[str]:
    """Every maximal horizontal/vertical run of 2+ letters on the grid."""
    return [text for text, _cells in _runs_with_cells(cells)]


def run_through(cells: dict[tuple[int, int], str], row: int, col: int,
                direction: str) -> str:
    """The maximal word-run passing through (row, col) in *direction*."""
    if (row, col) not in cells:
        return ""
    letters: list[str] = []
    if direction == ACROSS:
        while (row, col - 1) in cells:
            col -= 1
        while (row, col) in cells:
            letters.append(cells[(row, col)])
            col += 1
    else:
        while (row - 1, col) in cells:
            row -= 1
        while (row, col) in cells:
            letters.append(cells[(row, col)])
            row += 1
    return "".join(letters)


def build(words: list[str], seed: int = 0) -> Layout | None:
    """Weave *words* into a crossword. Deterministic for a given seed."""
    rng = random.Random(seed)
    pool: list[str] = []
    seen: set[str] = set()
    for raw in words:
        word = raw.strip().upper()
        if len(word) >= 3 and word.isalpha() and word not in seen:
            seen.add(word)
            pool.append(word)
    if not pool:
        return None
    pool.sort(key=lambda w: (-len(w), w))
    start = 0
    while start < len(pool):  # shuffle inside equal-length tiers for variety
        end = start
        while end < len(pool) and len(pool[end]) == len(pool[start]):
            end += 1
        tier = pool[start:end]
        rng.shuffle(tier)
        pool[start:end] = tier
        start = end

    cells: dict[tuple[int, int], str] = {}
    placements: list[Placement] = []
    placed_words: set[str] = set()

    def place(word: str, row0: int, col0: int, direction: str,
              new_cells: list[tuple[tuple[int, int], str]]) -> None:
        for (r, c), letter in new_cells:
            cells[(r, c)] = letter
        placements.append(Placement(word, row0, col0, direction))
        placed_words.add(word)

    first = pool[0]
    place(first, 0, 0, ACROSS, [((0, k), first[k]) for k in range(len(first))])

    deferred: list[str] = []
    for word in pool[1:]:
        best = _best(word, placements, cells, placed_words | {word})
        if best:
            _key, row0, col0, direction, new_cells = best
            place(word, row0, col0, direction, new_cells)
        else:
            deferred.append(word)
    for word in deferred:  # second pass: later words may open crossing spots
        best = _best(word, placements, cells, placed_words | {word})
        if best:
            _key, row0, col0, direction, new_cells = best
            place(word, row0, col0, direction, new_cells)

    dropped = [w for w in pool if w not in placed_words]
    _renumber(placements)
    _normalize_bounds(cells, placements)
    return Layout(cells=cells, placements=placements, dropped=dropped)


def _fits(cells: dict[tuple[int, int], str],
          new_cells: list[tuple[tuple[int, int], str]]) -> bool:
    for (r, c), letter in new_cells:
        existing = cells.get((r, c))
        if existing is not None and existing != letter:
            return False
    return True


def _validate(cells: dict[tuple[int, int], str],
              new_cells: list[tuple[tuple[int, int], str]],
              allowed: set[str], direction: str, word: str) -> bool:
    trial = dict(cells)
    for (r, c), letter in new_cells:
        trial[(r, c)] = letter
    if any(run not in allowed for run in runs(trial)):
        return False
    # The word must exactly fill its own maximal run: no stacking a short
    # word inside a longer one ("RENDERTEXT" over "RENDERTEXTTESTS").
    return run_through(trial, *new_cells[0][0], direction) == word


def _candidates(word: str, placements: list[Placement],
                cells: dict[tuple[int, int], str]):
    out = []
    for placed in placements:
        new_direction = DOWN if placed.direction == ACROSS else ACROSS
        for i, letter in enumerate(placed.word):
            if letter not in word:
                continue
            for j, candidate_letter in enumerate(word):
                if candidate_letter != letter:
                    continue
                if placed.direction == ACROSS:
                    # new word runs DOWN through (placed.row, placed.col + i)
                    row0, col0 = placed.row - j, placed.col + i
                    new_cells = [((row0 + k, col0), word[k]) for k in range(len(word))]
                else:
                    # new word runs ACROSS through (placed.row + i, placed.col)
                    row0, col0 = placed.row + i, placed.col - j
                    new_cells = [((row0, col0 + k), word[k]) for k in range(len(word))]
                if _fits(cells, new_cells):
                    out.append((row0, col0, new_direction, new_cells))
    return out


def _best(word: str, placements: list[Placement], cells: dict[tuple[int, int], str],
          allowed: set[str]):
    """Most crossings, then tightest bounding box; first found wins ties."""
    best = None
    for row0, col0, direction, new_cells in _candidates(word, placements, cells):
        if not _validate(cells, new_cells, allowed, direction, word):
            continue
        crossings = sum(1 for (r, c) in dict(new_cells) if (r, c) in cells)
        points = list(cells) + [rc for rc, _letter in new_cells]
        min_r, max_r = min(r for r, _ in points), max(r for r, _ in points)
        min_c, max_c = min(c for _, c in points), max(c for _, c in points)
        area = (max_r - min_r + 1) * (max_c - min_c + 1)
        key = (crossings, -area)
        if best is None or key > best[0]:
            best = (key, row0, col0, direction, new_cells)
    return best


def _renumber(placements: list[Placement]) -> None:
    starts = sorted({(p.row, p.col) for p in placements})
    numbers = {cell: n for n, cell in enumerate(starts, start=1)}
    for p in placements:
        p.number = numbers[(p.row, p.col)]


def _normalize_bounds(cells: dict[tuple[int, int], str],
                      placements: list[Placement]) -> None:
    if not cells:
        return
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    if min_r == 0 and min_c == 0:
        return
    shifted = {(r - min_r, c - min_c): letter for (r, c), letter in cells.items()}
    cells.clear()
    cells.update(shifted)
    for p in placements:
        p.row -= min_r
        p.col -= min_c
