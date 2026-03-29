"""Tests for qlib binary exporter."""

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from qlib_options.qlib_bin import export_bin


class TestQlibBinExport(unittest.TestCase):
    def _make_normalized_csv(self, tmpdir, symbol="SPY", dates=None, iv_values=None):
        if dates is None:
            dates = ["2026-01-02", "2026-01-03", "2026-01-06"]
        if iv_values is None:
            iv_values = [0.20, 0.22, 0.21]

        df = pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "atm_iv_30d": iv_values,
            "pcr_volume": [1.1, 1.2, 1.0],
            "pcr_oi": [0.9, 0.8, 0.85],
            "total_oi": [100000, 110000, 105000],
            "total_volume": [50000, 55000, 52000],
        })
        path = Path(tmpdir) / f"{symbol}.csv"
        df.to_csv(path, index=False)
        return path

    def test_create_mode(self):
        with tempfile.TemporaryDirectory() as norm_dir, tempfile.TemporaryDirectory() as qlib_dir:
            self._make_normalized_csv(norm_dir)
            export_bin(norm_dir, qlib_dir, mode="create")

            qlib_dir = Path(qlib_dir)
            # Check calendar
            cal = (qlib_dir / "calendars" / "day.txt").read_text().strip().splitlines()
            self.assertEqual(len(cal), 3)

            # Check instruments
            inst = (qlib_dir / "instruments" / "all.txt").read_text().strip()
            self.assertIn("SPY", inst)

            # Check feature bins exist
            bin_path = qlib_dir / "features" / "spy" / "atm_iv_30d.day.bin"
            self.assertTrue(bin_path.exists())

            # Verify binary content
            data = bin_path.read_bytes()
            values = struct.unpack(f"<{len(data) // 4}f", data)
            self.assertEqual(len(values), 3)
            self.assertAlmostEqual(values[0], 0.20, places=5)

    def test_overlay_mode_merges(self):
        with tempfile.TemporaryDirectory() as norm_dir, tempfile.TemporaryDirectory() as qlib_dir:
            qlib_dir = Path(qlib_dir)

            # Pre-existing calendar and instruments
            (qlib_dir / "calendars").mkdir(parents=True)
            (qlib_dir / "calendars" / "day.txt").write_text("2025-12-31\n")
            (qlib_dir / "instruments").mkdir(parents=True)
            (qlib_dir / "instruments" / "all.txt").write_text("AAPL\t2025-01-01\t2025-12-31\n")

            self._make_normalized_csv(norm_dir)
            export_bin(str(norm_dir), str(qlib_dir), mode="overlay")

            # Calendar should merge
            cal = (qlib_dir / "calendars" / "day.txt").read_text().strip().splitlines()
            self.assertIn("2025-12-31", cal)
            self.assertIn("2026-01-02", cal)

            # Instruments should merge
            inst = (qlib_dir / "instruments" / "all.txt").read_text()
            self.assertIn("AAPL", inst)
            self.assertIn("SPY", inst)


if __name__ == "__main__":
    unittest.main()
