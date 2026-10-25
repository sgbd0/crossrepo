"""Tests for the three renderers."""

import unittest

from crossrepo.layout import build
from crossrepo.render import render_html, render_json, render_text

CLUES = {"CAR": "A short drive", "ART": "Museum piece"}


class RenderTextTests(unittest.TestCase):
    def test_shows_clues_and_headers(self):
        layout = build(["CAR", "ART"], seed=1)
        text = render_text(layout, CLUES, title="t")
        self.assertIn("Across", text)
        self.assertIn("Down", text)
        self.assertIn("A short drive [3]", text)
        self.assertIn("Museum piece [3]", text)

    def test_blank_grid_hides_letters_but_shows_numbers(self):
        layout = build(["CAR", "ART"], seed=1)
        text = render_text(layout, CLUES)
        grid_section = text.split("\n\nAcross")[0]
        for letter in "CART":
            self.assertNotIn(f" {letter} ", grid_section)
        self.assertIn(" 1 ", grid_section)

    def test_reveal_shows_letters(self):
        layout = build(["CAR", "ART"], seed=1)
        text = render_text(layout, CLUES, reveal=True)
        self.assertIn(" C ", text)

    def test_missing_clue_gets_fallback(self):
        layout = build(["CAR", "ART"], seed=1)
        text = render_text(layout, {})
        self.assertIn("An identifier from this repo", text)


class RenderJsonTests(unittest.TestCase):
    def test_round_trip_shape(self):
        layout = build(["CAR", "ART"], seed=1)
        data = render_json(layout, CLUES, title="t", seed=1)
        self.assertEqual(data["tool"], "crossrepo")
        self.assertEqual(data["seed"], 1)
        self.assertEqual(data["size"]["rows"], layout.rows)
        self.assertEqual(len(data["grid"]), layout.rows)
        self.assertEqual(len(data["words"]), 2)
        for word in data["words"]:
            self.assertIn(word["direction"], ("across", "down"))
            self.assertEqual(len(word["answer"]), word["length"])
            self.assertTrue(word["clue"])

    def test_stats_meta_attached(self):
        layout = build(["CAR", "ART"], seed=1)
        data = render_json(layout, CLUES, meta={"files": 2})
        self.assertEqual(data["stats"], {"files": 2})


class RenderHtmlTests(unittest.TestCase):
    def test_is_self_contained(self):
        layout = build(["CAR", "ART"], seed=1)
        html = render_html(layout, CLUES, title="t & <b>", seed=1)
        self.assertIn("Reveal solution", html)
        self.assertIn('"words"', html)
        self.assertIn("A short drive", html)
        self.assertNotIn("t & <b>", html)  # title escaped
        self.assertIn("t &amp; &lt;b&gt;", html)

    def test_payload_carries_grid_and_answers(self):
        layout = build(["CAR", "ART"], seed=1)
        html = render_html(layout, CLUES, seed=3)
        self.assertIn('"seed": 3', html)
        for p in layout.placements:
            self.assertIn(p.word, html)


if __name__ == "__main__":
    unittest.main()
