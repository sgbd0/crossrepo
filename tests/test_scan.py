"""Tests for repository harvesting."""

import tempfile
import unittest
from pathlib import Path

from crossrepo.scan import harvest

SAMPLE = '''"""A sample package."""

MAX_SIZE = 128


class ValueStore:
    """Stores values for later lookup."""

    def put(self, key, value):
        return key, value


def flush_cache(store):
    """Drop every entry."""
    return []
'''


class HarvestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "pkg" / "sample.py").write_text(SAMPLE, encoding="utf-8")
        junk = self.root / "node_modules" / "left-pad"
        junk.mkdir(parents=True)
        (junk / "noise.py").write_text("SHOULD_NOT_SEE = 1\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_finds_symbols_with_facts(self):
        facts = harvest(self.root)
        by_name = {s.name: s for s in facts.symbols}
        self.assertEqual(by_name["ValueStore"].kind, "class")
        self.assertEqual(by_name["ValueStore"].docstring, "Stores values for later lookup.")
        self.assertEqual(by_name["ValueStore"].file, "pkg/sample.py")
        self.assertEqual(by_name["flush_cache"].kind, "function")
        self.assertEqual(by_name["flush_cache"].docstring, "Drop every entry.")
        self.assertEqual(by_name["MAX_SIZE"].kind, "constant")
        self.assertEqual(by_name["sample"].kind, "module")

    def test_skips_ignored_directories(self):
        facts = harvest(self.root)
        self.assertFalse(any("node_modules" in s.file for s in facts.symbols))
        self.assertFalse(any(s.name == "SHOULD_NOT_SEE" for s in facts.symbols))

    def test_reference_counts(self):
        facts = harvest(self.root)
        by_name = {s.name: s for s in facts.symbols}
        self.assertGreaterEqual(by_name["MAX_SIZE"].refs, 1)
        self.assertGreaterEqual(by_name["ValueStore"].refs, 1)

    def test_loc_counted(self):
        facts = harvest(self.root)
        self.assertGreaterEqual(facts.total_files, 2)
        self.assertGreater(facts.total_loc, 10)


class GenericModeTests(unittest.TestCase):
    def test_non_python_repo_uses_tokenizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.go").write_text(
                "func mainGrid() {}\n// mainGrid mainGrid\n", encoding="utf-8")
            facts = harvest(root)
            self.assertEqual(facts.mode, "generic")
            by_name = {s.name: s for s in facts.symbols}
            self.assertIn("mainGrid", by_name)
            self.assertGreaterEqual(by_name["mainGrid"].refs, 3)

    def test_empty_directory_degrades_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            facts = harvest(Path(tmp))
            self.assertEqual(facts.symbols, [])
            self.assertEqual(facts.total_files, 0)


if __name__ == "__main__":
    unittest.main()
