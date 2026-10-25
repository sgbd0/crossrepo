"""End-to-end CLI tests."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from crossrepo.cli import main

ALPHA = '''"""Demo package."""

MODE_BASIC = 1
GRID_LIMIT = 9


class Pipeline:
    """Moves items along."""

    def run(self):
        return 1


def reload_cache(pipe):
    """Refresh everything."""
    return pipe
'''


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "alpha.py").write_text(ALPHA, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, args, expect_stdout=True):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(args)
        return code, buffer.getvalue()

    def test_end_to_end_writes_all_formats(self):
        txt = self.root / "puzzle.txt"
        html = self.root / "puzzle.html"
        js = self.root / "puzzle.json"
        code, _ = self._run([str(self.root), "--txt", str(txt), "--html", str(html),
                             "--json", str(js), "--seed", "4",
                             "--title", "Demo - a crossword"])
        self.assertEqual(code, 0)
        self.assertTrue(txt.exists())
        self.assertTrue(html.exists())
        self.assertTrue(js.exists())
        self.assertIn("Across", txt.read_text(encoding="utf-8"))
        data = json.loads(js.read_text(encoding="utf-8"))
        self.assertEqual(data["tool"], "crossrepo")
        self.assertEqual(data["title"], "Demo - a crossword")
        self.assertGreaterEqual(len(data["words"]), 4)
        self.assertIn("Reveal solution", html.read_text(encoding="utf-8"))

    def test_stdout_mode_prints_puzzle(self):
        code, out = self._run([str(self.root), "--seed", "2"])
        self.assertEqual(code, 0)
        self.assertIn("Across", out)
        self.assertIn("Down", out)

    def test_stats_only(self):
        code, out = self._run([str(self.root), "--stats"])
        self.assertEqual(code, 0)
        self.assertIn("code files", out)
        self.assertIn("symbols", out)

    def test_missing_root_fails_cleanly(self):
        code, _ = self._run(["Z:/definitely/not/a/repo"])
        self.assertEqual(code, 2)

    def test_reveal_flag_fills_grid(self):
        code, out = self._run([str(self.root), "--reveal", "--seed", "2"])
        self.assertEqual(code, 0)
        self.assertNotIn(" . ", out)


if __name__ == "__main__":
    unittest.main()
