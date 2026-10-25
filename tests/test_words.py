"""Tests for word mining and filtering."""

import unittest
from pathlib import Path

from crossrepo.scan import RepoFacts, Symbol
from crossrepo.words import build_words, normalize, split_identifier


def _facts():
    facts = RepoFacts(root=Path("."), name="demo")
    facts.symbols = [
        Symbol("LayoutEngine", "class", "x.py", 1, refs=10),
        Symbol("layout_engine", "function", "x.py", 5, refs=4),
        Symbol("render_text", "function", "r.py", 2, refs=7),
        Symbol("_private_helper", "function", "r.py", 3, refs=1),
        Symbol("__dunder__", "function", "r.py", 4, refs=0),
        Symbol("ab", "constant", "r.py", 6, refs=1),
        Symbol("the", "constant", "r.py", 7, refs=1),
        Symbol("grid", "method", "x.py", 9, refs=3),
    ]
    return facts


class NormalizeTests(unittest.TestCase):
    def test_strips_separators_and_digits(self):
        self.assertEqual(normalize("layout_engine"), "LAYOUTENGINE")
        self.assertEqual(normalize("a1b_c2"), "ABC")
        self.assertEqual(normalize("Grid"), "GRID")

    def test_split_identifier(self):
        self.assertEqual(split_identifier("render_html_page"), ["render", "html", "page"])
        self.assertEqual(split_identifier("LayoutEngine"), ["Layout", "Engine"])
        self.assertEqual(split_identifier("HTTPServer"), ["HTTP", "Server"])


class BuildWordsTests(unittest.TestCase):
    def test_dedupes_normalization_collisions_by_best_symbol(self):
        words = {w.text: w for w in build_words(_facts())}
        self.assertIn("LAYOUTENGINE", words)
        self.assertEqual(words["LAYOUTENGINE"].symbol.kind, "class")

    def test_skips_private_dunder_short_and_stopwords(self):
        texts = {w.text for w in build_words(_facts())}
        self.assertNotIn("PRIVATEHELPER", texts)
        self.assertNotIn("DUNDER", texts)
        self.assertNotIn("AB", texts)
        self.assertNotIn("THE", texts)

    def test_adds_repo_name_as_answer(self):
        words = {w.text: w for w in build_words(_facts())}
        self.assertIn("DEMO", words)
        self.assertEqual(words["DEMO"].symbol.kind, "repo")

    def test_fragments_come_from_split_identifiers(self):
        words = build_words(_facts())
        fragments = [w for w in words if w.is_fragment]
        self.assertTrue(any(f.text == "LAYOUT" and f.parent == "LayoutEngine"
                            for f in fragments))

    def test_limit_is_respected_for_main_words(self):
        facts = _facts()
        facts.symbols = [Symbol(f"symbol_{i}", "function", "x.py", i, refs=i)
                         for i in range(30)]
        words = build_words(facts, limit=10)
        main = [w for w in words if not w.is_fragment and w.symbol.kind != "repo"]
        self.assertLessEqual(len(main), 10)


if __name__ == "__main__":
    unittest.main()
