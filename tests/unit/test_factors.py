"""Unit tests for OptionsFactorDeriver — ported from qlib upstream scaffolding."""

import unittest

import numpy as np
import pandas as pd

from qlib_options.factors import OptionsFactorDeriver
from qlib_options.schemas import FACTOR_COLUMNS


def make_chain(
    spot=100.0,
    strikes=None,
    expiries_dte=None,
    call_ivs=None,
    put_ivs=None,
    call_volumes=None,
    put_volumes=None,
    call_ois=None,
    put_ois=None,
    snapshot_date="2026-01-15",
):
    """Build a synthetic options chain DataFrame for testing."""
    if strikes is None:
        strikes = [90, 95, 100, 105, 110]
    if expiries_dte is None:
        expiries_dte = [20, 40]
    if call_ivs is None:
        call_ivs = {s: 0.25 for s in strikes}
    if put_ivs is None:
        put_ivs = {s: 0.30 for s in strikes}
    if call_volumes is None:
        call_volumes = {s: 1000 for s in strikes}
    if put_volumes is None:
        put_volumes = {s: 800 for s in strikes}
    if call_ois is None:
        call_ois = {s: 5000 for s in strikes}
    if put_ois is None:
        put_ois = {s: 4000 for s in strikes}

    ref = pd.Timestamp(snapshot_date)
    rows = []
    for dte in expiries_dte:
        expiry = ref + pd.Timedelta(days=dte)
        for strike in strikes:
            for otype, ivs, vols, ois in [
                ("C", call_ivs, call_volumes, call_ois),
                ("P", put_ivs, put_volumes, put_ois),
            ]:
                rows.append({
                    "snapshot_date": snapshot_date,
                    "symbol": "TEST",
                    "spot_price": spot,
                    "expiry": expiry,
                    "strike": float(strike),
                    "option_type": otype,
                    "bid": spot * 0.05 if otype == "C" else spot * 0.04,
                    "ask": spot * 0.06 if otype == "C" else spot * 0.05,
                    "last": spot * 0.055,
                    "volume": float(vols.get(strike, 0)),
                    "open_interest": float(ois.get(strike, 0)),
                    "implied_volatility": float(ivs.get(strike, 0.25)),
                    "in_the_money": (otype == "C" and strike < spot)
                    or (otype == "P" and strike > spot),
                    "contract_symbol": f"TEST{expiry.strftime('%y%m%d')}{otype}{int(strike*1000):08d}",
                })

    return pd.DataFrame(rows)


class TestOptionsFactorDeriver(unittest.TestCase):
    def setUp(self):
        self.deriver = OptionsFactorDeriver()

    def test_atm_iv_30d_interpolation(self):
        chain = make_chain(
            spot=100.0,
            strikes=[98, 100, 102],
            expiries_dte=[20, 40],
            call_ivs={98: 0.22, 100: 0.20, 102: 0.18},
            put_ivs={98: 0.23, 100: 0.21, 102: 0.19},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertAlmostEqual(result["atm_iv_30d"], 0.205, places=3)

    def test_atm_iv_30d_different_expiry_ivs(self):
        rows = []
        ref = pd.Timestamp("2026-01-15")
        for otype in ["C", "P"]:
            rows.append({
                "snapshot_date": "2026-01-15", "symbol": "TEST", "spot_price": 100.0,
                "expiry": ref + pd.Timedelta(days=20), "strike": 100.0,
                "option_type": otype, "bid": 5.0, "ask": 6.0, "last": 5.5,
                "volume": 1000.0, "open_interest": 5000.0,
                "implied_volatility": 0.30, "in_the_money": False,
                "contract_symbol": f"TEST{otype}20",
            })
        for otype in ["C", "P"]:
            rows.append({
                "snapshot_date": "2026-01-15", "symbol": "TEST", "spot_price": 100.0,
                "expiry": ref + pd.Timedelta(days=40), "strike": 100.0,
                "option_type": otype, "bid": 5.0, "ask": 6.0, "last": 5.5,
                "volume": 1000.0, "open_interest": 5000.0,
                "implied_volatility": 0.20, "in_the_money": False,
                "contract_symbol": f"TEST{otype}40",
            })
        chain = pd.DataFrame(rows)
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertAlmostEqual(result["atm_iv_30d"], 0.25, places=3)

    def test_atm_iv_30d_single_expiry(self):
        chain = make_chain(
            spot=100.0, strikes=[100], expiries_dte=[45],
            call_ivs={100: 0.28}, put_ivs={100: 0.28},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertAlmostEqual(result["atm_iv_30d"], 0.28, places=3)

    def test_pcr_volume(self):
        chain = make_chain(
            spot=100.0, strikes=[100], expiries_dte=[30],
            call_volumes={100: 1000}, put_volumes={100: 1500},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertAlmostEqual(result["pcr_volume"], 1.5, places=3)

    def test_pcr_oi(self):
        chain = make_chain(
            spot=100.0, strikes=[100], expiries_dte=[30],
            call_ois={100: 10000}, put_ois={100: 8000},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertAlmostEqual(result["pcr_oi"], 0.8, places=3)

    def test_pcr_excludes_leaps(self):
        chain = make_chain(
            spot=100.0, strikes=[100], expiries_dte=[30, 365],
            call_volumes={100: 1000}, put_volumes={100: 2000},
            call_ois={100: 5000}, put_ois={100: 3000},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertAlmostEqual(result["pcr_volume"], 2.0, places=3)
        self.assertEqual(result["total_volume"], 2 * (1000 + 2000))
        self.assertEqual(result["total_oi"], 2 * (5000 + 3000))

    def test_pcr_zero_calls_returns_nan(self):
        chain = make_chain(
            spot=100.0, strikes=[100], expiries_dte=[30],
            call_volumes={100: 0}, put_volumes={100: 500},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertTrue(np.isnan(result["pcr_volume"]))

    def test_empty_chain_returns_all_nan(self):
        result = self.deriver.derive_all(pd.DataFrame(), spot_price=100.0)
        for col in FACTOR_COLUMNS:
            self.assertTrue(np.isnan(result[col]), f"{col} should be NaN")

    def test_nan_spot_returns_all_nan(self):
        chain = make_chain()
        result = self.deriver.derive_all(chain, spot_price=np.nan)
        for col in FACTOR_COLUMNS:
            self.assertTrue(np.isnan(result[col]), f"{col} should be NaN")

    def test_output_columns_match(self):
        chain = make_chain()
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertEqual(sorted(result.index.tolist()), sorted(FACTOR_COLUMNS))

    def test_total_oi_and_volume(self):
        chain = make_chain(
            spot=100.0, strikes=[100, 110], expiries_dte=[30],
            call_volumes={100: 500, 110: 300}, put_volumes={100: 400, 110: 200},
            call_ois={100: 1000, 110: 800}, put_ois={100: 900, 110: 700},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertEqual(result["total_volume"], 500 + 300 + 400 + 200)
        self.assertEqual(result["total_oi"], 1000 + 800 + 900 + 700)

    def test_expired_contracts_excluded(self):
        chain = make_chain(
            spot=100.0, strikes=[100], expiries_dte=[-1, 30],
            call_volumes={100: 1000}, put_volumes={100: 500},
        )
        result = self.deriver.derive_all(chain, spot_price=100.0)
        self.assertEqual(result["total_volume"], 1000 + 500)


if __name__ == "__main__":
    unittest.main()
