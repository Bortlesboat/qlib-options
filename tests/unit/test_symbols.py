"""Tests for symbol loading."""

import tempfile
import unittest
from pathlib import Path

from qlib_options.symbols import load_symbols


class TestSymbols(unittest.TestCase):
    def test_explicit_symbols(self):
        result = load_symbols(symbols_arg="SPY,QQQ,AAPL")
        self.assertEqual(result, ["AAPL", "QQQ", "SPY"])

    def test_symbols_uppercased(self):
        result = load_symbols(symbols_arg="spy,qqq")
        self.assertEqual(result, ["QQQ", "SPY"])

    def test_symbols_deduplicated(self):
        result = load_symbols(symbols_arg="SPY,SPY,QQQ")
        self.assertEqual(result, ["QQQ", "SPY"])

    def test_symbols_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# comment\nSPY\nQQQ\nAAPL\n")
            f.flush()
            result = load_symbols(symbols_file=f.name)
        self.assertEqual(result, ["AAPL", "QQQ", "SPY"])

    def test_symbols_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_symbols(symbols_file="/nonexistent/path.txt")

    def test_default_universe_loads(self):
        result = load_symbols()
        self.assertIn("SPY", result)
        self.assertIn("QQQ", result)
        self.assertGreater(len(result), 10)


if __name__ == "__main__":
    unittest.main()
