"""Options chain snapshot collector using yahooquery.

This is a snapshot-only collector. yahooquery provides the current options chain,
not historical data. Run daily (e.g., via cron) to build a historical dataset.
"""

import datetime
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from qlib_options.schemas import RAW_COLUMNS

logger = logging.getLogger(__name__)


def collect_snapshot(
    symbols: list[str],
    raw_dir: str | Path,
    delay: float = 1.0,
) -> dict[str, int]:
    """Collect current options chain snapshots for given symbols.

    Parameters
    ----------
    symbols : list[str]
        Ticker symbols to collect.
    raw_dir : str or Path
        Directory to save raw chain CSVs (one per symbol, append-safe).
    delay : float
        Seconds to sleep between API calls.

    Returns
    -------
    dict with keys 'success', 'failed', 'skipped' (counts).
    """
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stats = {"success": 0, "failed": 0, "skipped": 0}

    for i, symbol in enumerate(symbols):
        if i > 0:
            time.sleep(delay)

        logger.info(f"[{i + 1}/{len(symbols)}] Collecting {symbol}...")
        try:
            df = _fetch_chain(symbol)
        except Exception as e:
            logger.warning(f"{symbol}: fetch failed: {e}")
            stats["failed"] += 1
            continue

        if df.empty:
            logger.info(f"{symbol}: no options data, skipping")
            stats["skipped"] += 1
            continue

        _save_raw(df, symbol, raw_dir)
        stats["success"] += 1
        logger.info(f"{symbol}: {len(df)} contracts saved")

    return stats


def _fetch_chain(symbol: str) -> pd.DataFrame:
    """Fetch current options chain + spot price via yahooquery."""
    from yahooquery import Ticker

    ticker = Ticker(symbol, asynchronous=False)

    # Get raw spot price
    price_data = ticker.price
    if isinstance(price_data, dict) and symbol in price_data:
        spot = price_data[symbol].get("regularMarketPrice", np.nan)
    else:
        spot = np.nan

    # Get options chain
    chain_df = ticker.option_chain
    if isinstance(chain_df, (dict, str)) or chain_df is None:
        return pd.DataFrame()
    if chain_df.empty:
        return pd.DataFrame()

    chain_df = chain_df.reset_index()
    now = datetime.datetime.utcnow()
    today = pd.Timestamp(now.date())

    result = pd.DataFrame({
        "snapshot_date": today,
        "snapshot_ts": now.isoformat(),
        "symbol": symbol.upper(),
        "spot_price": spot,
        "expiry": pd.to_datetime(chain_df.get("expiration", pd.NaT)),
        "strike": pd.to_numeric(chain_df.get("strike", np.nan), errors="coerce"),
        "option_type": chain_df.get("optionType", "").map(
            lambda x: "C" if str(x).lower().startswith("call") else "P"
        ),
        "bid": pd.to_numeric(chain_df.get("bid", np.nan), errors="coerce"),
        "ask": pd.to_numeric(chain_df.get("ask", np.nan), errors="coerce"),
        "last": pd.to_numeric(chain_df.get("lastPrice", np.nan), errors="coerce"),
        "volume": pd.to_numeric(chain_df.get("volume", np.nan), errors="coerce"),
        "open_interest": pd.to_numeric(chain_df.get("openInterest", np.nan), errors="coerce"),
        "implied_volatility": pd.to_numeric(
            chain_df.get("impliedVolatility", np.nan), errors="coerce"
        ),
        "in_the_money": chain_df.get("inTheMoney", False),
        "contract_symbol": chain_df.get("contractSymbol", ""),
    })

    return result


def _save_raw(df: pd.DataFrame, symbol: str, raw_dir: Path):
    """Append-safe save: deduplicates by (snapshot_date, contract_symbol)."""
    fname = symbol.upper().replace(".", "_").replace("/", "_")
    path = raw_dir / f"{fname}.csv"

    if path.exists():
        old_df = pd.read_csv(path)
        df = pd.concat([old_df, df], sort=False)
        df = df.drop_duplicates(subset=["snapshot_date", "contract_symbol"], keep="last")

    df.to_csv(path, index=False)
