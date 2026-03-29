"""CLI smoke tests."""

import unittest

from qlib_options.cli import main


class TestCLI(unittest.TestCase):
    def test_version(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_no_args_shows_help(self):
        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_snapshot_requires_raw_dir(self):
        with self.assertRaises(SystemExit):
            main(["snapshot", "--symbols", "SPY"])

    def test_derive_requires_both_dirs(self):
        with self.assertRaises(SystemExit):
            main(["derive", "--raw-dir", "/tmp/raw"])

    def test_export_bin_requires_args(self):
        with self.assertRaises(SystemExit):
            main(["export-bin"])


if __name__ == "__main__":
    unittest.main()
