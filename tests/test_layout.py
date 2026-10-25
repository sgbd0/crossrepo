"""Tests for the crossword layout engine."""

import unittest

from crossrepo.layout import ACROSS, DOWN, build, run_through, runs

WORDS = [
    "CROSSWORD", "REPOSITORY", "PLACEMENT", "LAYOUT", "ENGINE", "GRID",
    "CLUE", "ACROSS", "DOWNWARD", "PUZZLE", "SEED", "CELLS",
]


class BuildTests(unittest.TestCase):
    def test_places_majority_of_words(self):
        layout = build(WORDS, seed=3)
        self.assertIsNotNone(layout)
        self.assertGreaterEqual(len(layout.placements), 8)
        self.assertLessEqual(len(layout.dropped), 3)

    def test_runs_invariant_every_run_is_a_placed_word(self):
        for seed in range(5):
            layout = build(WORDS, seed=seed)
            placed = {p.word for p in layout.placements}
            for run in runs(layout.cells):
                self.assertIn(run, placed, f"seed={seed} run={run}")

    def test_each_word_exactly_fills_its_own_run(self):
        for seed in range(5):
            layout = build(WORDS, seed=seed)
            for p in layout.placements:
                self.assertEqual(run_through(layout.cells, p.row, p.col, p.direction),
                                 p.word, f"seed={seed} word={p.word}")

    def test_shorter_word_never_stacks_inside_longer_one(self):
        # Regression: RENDERTEXT used to be laid on top of RENDERTEXTTESTS,
        # producing two Across clues with the same number.
        layout = build(["RENDERTEXTTESTS", "RENDERTEXT", "RENDER"], seed=2)
        for p in layout.placements:
            self.assertEqual(run_through(layout.cells, p.row, p.col, p.direction), p.word)
        starts = [(p.row, p.col, p.direction) for p in layout.placements]
        self.assertEqual(len(starts), len(set(starts)))

    def test_every_word_after_first_crosses_another(self):
        layout = build(WORDS, seed=7)
        cell_sets = []
        for p in layout.placements:
            cells = set()
            for k in range(len(p.word)):
                if p.direction == ACROSS:
                    cells.add((p.row, p.col + k))
                else:
                    cells.add((p.row + k, p.col))
            cell_sets.append(cells)
        for idx, cells in enumerate(cell_sets):
            if idx == 0:
                continue
            self.assertTrue(
                any(cells & other for j, other in enumerate(cell_sets) if j != idx),
                f"{layout.placements[idx].word} floats free")

    def test_deterministic_for_same_seed(self):
        def fingerprint(layout):
            return [(p.word, p.row, p.col, p.direction) for p in layout.placements]
        self.assertEqual(fingerprint(build(WORDS, seed=11)),
                         fingerprint(build(WORDS, seed=11)))

    def test_numbers_dense_from_one_and_shared_starts(self):
        layout = build(WORDS, seed=13)
        numbers = sorted({p.number for p in layout.placements})
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        starts = {}
        for p in layout.placements:
            starts.setdefault((p.row, p.col), set()).add(p.number)
        for cell_numbers in starts.values():
            self.assertEqual(len(cell_numbers), 1)

    def test_two_words_share_a_letter_correctly(self):
        layout = build(["CAR", "ART"], seed=1)
        self.assertEqual(len(layout.placements), 2)
        placed = {p.word for p in layout.placements}
        # The naive CAR-across + ART-down-below placement would spell CART;
        # the invariant must reject it and pick a legal crossing instead.
        self.assertNotIn("CART", runs(layout.cells))

    def test_filters_non_alpha_and_short_words(self):
        self.assertIsNone(build(["ab", "x1y", "", "  "], seed=0))

    def test_bounds_are_normalized_to_zero(self):
        layout = build(WORDS, seed=21)
        self.assertGreaterEqual(min(r for r, _ in layout.cells), 0)
        self.assertGreaterEqual(min(c for _, c in layout.cells), 0)
        self.assertEqual(layout.rows, max(r for r, _ in layout.cells) + 1)


if __name__ == "__main__":
    unittest.main()
