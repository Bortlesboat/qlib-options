"""Native qlib binary exporter — no pyqlib dependency required.

Writes qlib-compatible day-frequency binary feature files from normalized CSVs.
Supports 'create' mode (new dataset) and 'overlay' mode (augment existing).

Binary format: np.float32 array, one value per calendar day, stored as
  features/<SYMBOL>/<field>.day.bin
Plus:
  calendars/day.txt     — one YYYY-MM-DD per line
  instruments/all.txt   — SYMBOL<tab>START<tab>END per line
"""

import logging
import struct
from pathlib import Path

import numpy as np
import pandas as pd

from qlib_options.schemas import FACTOR_COLUMNS

logger = logging.getLogger(__name__)


def export_bin(
    normalized_dir: str | Path,
    qlib_dir: str | Path,
    mode: str = "overlay",
):
    """Export normalized CSVs to qlib binary format.

    Parameters
    ----------
    normalized_dir : str or Path
        Directory with normalized factor CSVs.
    qlib_dir : str or Path
        Target qlib data directory. In 'overlay' mode, existing calendars
        and instruments are merged; in 'create' mode, only options data
        is written.
    mode : str
        'create' — fresh dataset (overwrites target).
        'overlay' — merge into existing qlib data root.
    """
    normalized_dir = Path(normalized_dir)
    qlib_dir = Path(qlib_dir)

    if mode not in ("create", "overlay"):
        raise ValueError(f"mode must be 'create' or 'overlay', got '{mode}'")

    csv_files = sorted(normalized_dir.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No normalized data in {normalized_dir}")
        return

    # Collect all dates and instruments
    all_dates = set()
    instruments = {}  # symbol -> (start, end)

    for fpath in csv_files:
        df = pd.read_csv(fpath)
        if df.empty or "date" not in df.columns:
            continue

        df["date"] = pd.to_datetime(df["date"])
        symbol = df["symbol"].dropna().iloc[0] if "symbol" in df.columns else fpath.stem.upper()
        symbol = symbol.upper()

        dates = df["date"].dropna()
        if dates.empty:
            continue

        all_dates.update(dates.dt.strftime("%Y-%m-%d").tolist())
        instruments[symbol] = (
            dates.min().strftime("%Y-%m-%d"),
            dates.max().strftime("%Y-%m-%d"),
        )

        # Write feature bins
        features_dir = qlib_dir / "features" / symbol.lower()
        features_dir.mkdir(parents=True, exist_ok=True)

        for col in FACTOR_COLUMNS:
            if col not in df.columns:
                continue
            values = df[col].values.astype(np.float32)
            bin_path = features_dir / f"{col}.day.bin"
            with open(bin_path, "wb") as f:
                f.write(struct.pack(f"<{len(values)}f", *values))

        logger.info(f"{symbol}: wrote {len(dates)} days of factor bins")

    # Write/merge calendars
    cal_dir = qlib_dir / "calendars"
    cal_dir.mkdir(parents=True, exist_ok=True)
    cal_path = cal_dir / "day.txt"

    if mode == "overlay" and cal_path.exists():
        existing_dates = set(cal_path.read_text().strip().splitlines())
        all_dates.update(existing_dates)

    sorted_dates = sorted(all_dates)
    cal_path.write_text("\n".join(sorted_dates) + "\n")

    # Write/merge instruments
    inst_dir = qlib_dir / "instruments"
    inst_dir.mkdir(parents=True, exist_ok=True)
    inst_path = inst_dir / "all.txt"

    existing_instruments = {}
    if mode == "overlay" and inst_path.exists():
        for line in inst_path.read_text().strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                existing_instruments[parts[0]] = (parts[1], parts[2])

    # Merge: extend date ranges for existing symbols
    for sym, (start, end) in instruments.items():
        if sym in existing_instruments:
            old_start, old_end = existing_instruments[sym]
            start = min(start, old_start)
            end = max(end, old_end)
        existing_instruments[sym] = (start, end)

    lines = [f"{sym}\t{s}\t{e}" for sym, (s, e) in sorted(existing_instruments.items())]
    inst_path.write_text("\n".join(lines) + "\n")

    logger.info(
        f"Exported {len(instruments)} symbols, {len(sorted_dates)} calendar days "
        f"to {qlib_dir} (mode={mode})"
    )
