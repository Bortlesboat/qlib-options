"""Normalize derived factors to a trading calendar."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def get_us_trading_calendar(start_date=None, end_date=None):
    """Get US trading days using exchange_calendars (NYSE/XNYS).

    Returns
    -------
    pd.DatetimeIndex
        Trading days in the requested range.
    """
    import exchange_calendars as xcals

    cal = xcals.get_calendar("XNYS")
    sessions = cal.sessions
    if start_date:
        sessions = sessions[sessions >= pd.Timestamp(start_date)]
    if end_date:
        sessions = sessions[sessions <= pd.Timestamp(end_date)]
    return sessions


def normalize_factors(
    derived_dir: str | Path,
    normalized_dir: str | Path,
):
    """Normalize derived factor CSVs to US trading calendar.

    No forward-fill: missing snapshot dates remain NaN. Downstream
    handlers/processors decide fill strategy.

    Parameters
    ----------
    derived_dir : str or Path
        Directory with derived factor CSVs.
    normalized_dir : str or Path
        Output directory for normalized CSVs.
    """
    derived_dir = Path(derived_dir)
    normalized_dir = Path(normalized_dir)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(derived_dir.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No derived data found in {derived_dir}")
        return

    for fpath in csv_files:
        try:
            df = pd.read_csv(fpath)
        except Exception as e:
            logger.warning(f"Failed to read {fpath}: {e}")
            continue

        if df.empty:
            continue

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep="last")]

        if df.empty:
            continue

        # Align to trading calendar
        calendar = get_us_trading_calendar(
            start_date=df.index.min(),
            end_date=df.index.max(),
        )
        df = df.reindex(calendar)

        # Preserve symbol
        if "symbol" in df.columns:
            symbol_val = df["symbol"].dropna()
            if not symbol_val.empty:
                df["symbol"] = symbol_val.iloc[0]

        df.sort_index(inplace=True)
        df.index.name = "date"
        df.reset_index().to_csv(normalized_dir / fpath.name, index=False)

    logger.info(f"Normalized {len(csv_files)} files to {normalized_dir}")
