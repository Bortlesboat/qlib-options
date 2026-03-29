"""Options factor derivation — transforms raw chain snapshots into daily factors.

Reused from the qlib upstream scaffolding with minimal changes:
- Removed qlib/loguru imports
- Uses stdlib logging
- Same factor logic, same column names, same test compatibility
"""

import logging

import numpy as np
import pandas as pd

from qlib_options.schemas import FACTOR_COLUMNS

logger = logging.getLogger(__name__)


class OptionsFactorDeriver:
    """Transforms raw options chain snapshots into underlying-level daily factors.

    Each public factor method takes a single-date chain DataFrame and returns a scalar.
    ``derive_all`` orchestrates all factors and returns a single-row Series.

    Factors:
        atm_iv_30d   - ATM implied volatility interpolated to 30-day tenor
        pcr_volume   - Put/call ratio by volume (near-term, DTE <= 180)
        pcr_oi       - Put/call ratio by open interest (near-term, DTE <= 180)
        total_oi     - Total open interest across all contracts
        total_volume - Total volume across all contracts
    """

    FACTOR_COLUMNS = FACTOR_COLUMNS
    NEAR_TERM_MAX_DTE = 180

    def derive_all(self, chain_df: pd.DataFrame, spot_price: float) -> pd.Series:
        """Compute all factors for one symbol on one snapshot date.

        Parameters
        ----------
        chain_df : pd.DataFrame
            Raw chain for one symbol, one snapshot date.
        spot_price : float
            Raw (unadjusted) underlying price at time of snapshot.

        Returns
        -------
        pd.Series with FACTOR_COLUMNS as index. Missing data -> NaN.
        """
        if chain_df is None or chain_df.empty or np.isnan(spot_price):
            return pd.Series({col: np.nan for col in self.FACTOR_COLUMNS})

        chain = chain_df.copy()
        chain["expiry"] = pd.to_datetime(chain["expiry"])

        if "snapshot_date" in chain.columns:
            ref_date = pd.to_datetime(chain["snapshot_date"].iloc[0])
        else:
            ref_date = pd.Timestamp.now().normalize()
        chain["dte"] = (chain["expiry"] - ref_date).dt.days
        chain = chain[chain["dte"] > 0]

        if chain.empty:
            return pd.Series({col: np.nan for col in self.FACTOR_COLUMNS})

        return pd.Series({
            "atm_iv_30d": self.atm_iv_30d(chain, spot_price),
            "pcr_volume": self.put_call_ratio_volume(chain),
            "pcr_oi": self.put_call_ratio_oi(chain),
            "total_oi": float(chain["open_interest"].sum()),
            "total_volume": float(chain["volume"].sum()),
        })

    def atm_iv_30d(self, chain: pd.DataFrame, spot: float) -> float:
        """ATM IV interpolated to 30-day tenor."""
        target_dte = 30
        expiries = sorted(chain["dte"].unique())

        if not expiries:
            return np.nan

        lower = [d for d in expiries if d <= target_dte]
        upper = [d for d in expiries if d > target_dte]

        if lower and upper:
            dte_lo, dte_hi = max(lower), min(upper)
            iv_lo = self._atm_iv_for_dte(chain, dte_lo, spot)
            iv_hi = self._atm_iv_for_dte(chain, dte_hi, spot)
            if np.isnan(iv_lo) and np.isnan(iv_hi):
                return np.nan
            if np.isnan(iv_lo):
                return iv_hi
            if np.isnan(iv_hi):
                return iv_lo
            weight = (target_dte - dte_lo) / (dte_hi - dte_lo)
            return float(iv_lo + weight * (iv_hi - iv_lo))
        elif lower:
            return self._atm_iv_for_dte(chain, max(lower), spot)
        else:
            return self._atm_iv_for_dte(chain, min(upper), spot)

    @staticmethod
    def _atm_iv_for_dte(chain: pd.DataFrame, dte: int, spot: float) -> float:
        """ATM IV for a specific DTE: average of nearest-strike call and put IV."""
        sub = chain[(chain["dte"] == dte) & (chain["implied_volatility"] > 0)].copy()
        if sub.empty:
            return np.nan
        sub["dist"] = (sub["strike"] - spot).abs()
        atm_strike = sub.loc[sub["dist"].idxmin(), "strike"]
        ivs = sub.loc[sub["strike"] == atm_strike, "implied_volatility"].dropna().values
        return float(np.nanmean(ivs)) if len(ivs) > 0 else np.nan

    def put_call_ratio_volume(self, chain: pd.DataFrame) -> float:
        """Put/call ratio by volume, near-term only (DTE <= 180)."""
        return self._pcr(chain[chain["dte"] <= self.NEAR_TERM_MAX_DTE], "volume")

    def put_call_ratio_oi(self, chain: pd.DataFrame) -> float:
        """Put/call ratio by open interest, near-term only (DTE <= 180)."""
        return self._pcr(chain[chain["dte"] <= self.NEAR_TERM_MAX_DTE], "open_interest")

    @staticmethod
    def _pcr(chain: pd.DataFrame, field: str) -> float:
        if chain.empty:
            return np.nan
        call_sum = chain.loc[chain["option_type"] == "C", field].sum()
        put_sum = chain.loc[chain["option_type"] == "P", field].sum()
        if call_sum == 0 or np.isnan(call_sum):
            return np.nan
        return float(put_sum / call_sum)
