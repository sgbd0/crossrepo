"""Tests for clue writing."""

import random
import unittest
from pathlib import Path

from crossrepo.clues import make_clues
from crossrepo.scan import RepoFacts, Symbol
from crossrepo.words import Word


def _words():
    return [
        Word("VALUESTORE", Symbol("ValueStore", "class", "pkg/store.py", 3,
                                  docstring="Stores values for later lookup.", refs=5)),
        Word("FLUSHCACHE", Symbol("flush_cache", "function", "pkg/store.py", 12,
                                  docstring="Drop every entry.", refs=2)),
        Word("ALPHA", Symbol("alpha", "module", "alpha.py", 1, refs=1)),
        Word("ENGINE", Symbol("LayoutEngine", "class", "x.py", 1),
             is_fragment=True, parent="LayoutEngine"),
    ]


class ClueTests(unittest.TestCase):
    def setUp(self):
        self.facts = RepoFacts(root=Path("."), name="demo")

    def test_clues_never_leak_the_answer(self):
        clues = make_clues(_words(), self.facts, random.Random(1))
        for answer, clue in clues.items():
            if answer == "ENGINE":  # fragments deliberately hint via parent
                continue
            self.assertNotIn(answer.lower(), clue.lower(), (answer, clue))

    def test_deterministic_for_same_seed(self):
        first = make_clues(_words(), self.facts, random.Random(42))
        second = make_clues(_words(), self.facts, random.Random(42))
        self.assertEqual(first, second)

    def test_fragment_clue_names_the_parent(self):
        clues = make_clues(_words(), self.facts, random.Random(1))
        self.assertIn("LayoutEngine", clues["ENGINE"])

    def test_repo_kind_gets_special_clue(self):
        word = Word("DEMO", Symbol("demo", "repo", refs=10**6))
        clues = make_clues([word], self.facts, random.Random(1))
        self.assertIn("repository", clues["DEMO"])

    def test_every_word_gets_a_clue(self):
        clues = make_clues(_words(), self.facts, random.Random(1))
        self.assertEqual(set(clues), {w.text for w in _words()})

    def test_docstring_clue_is_shortened(self):
        long_doc = "x" * 300
        word = Word("BIG", Symbol("big", "function", "b.py", 1, docstring=long_doc))
        clues = make_clues([word], self.facts, random.Random(1))
        self.assertLessEqual(len(clues["BIG"]), 160)


if __name__ == "__main__":
    unittest.main()
