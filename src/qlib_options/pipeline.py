"""Full pipeline orchestrator — snapshot -> derive -> normalize -> export."""

import logging
from pathlib import Path

import pandas as pd

from qlib_options.collector import collect_snapshot
from qlib_options.factors import OptionsFactorDeriver
from qlib_options.normalize import normalize_factors
from qlib_options.qlib_bin import export_bin

logger = logging.getLogger(__name__)


def derive_factors(raw_dir: str | Path, derived_dir: str | Path):
    """Stage 2: Derive underlying-level factors from raw chain snapshots.

    Reads raw CSVs from raw_dir, groups by snapshot_date, computes factors,
    and writes one-row-per-date CSVs to derived_dir.
    """
    raw_dir = Path(raw_dir)
    derived_dir = Path(derived_dir)
    derived_dir.mkdir(parents=True, exist_ok=True)

    deriver = OptionsFactorDeriver()
    source_files = sorted(raw_dir.glob("*.csv"))

    if not source_files:
        logger.warning(f"No raw data found in {raw_dir}")
        return

    for fpath in source_files:
        try:
            raw_df = pd.read_csv(fpath)
        except Exception as e:
            logger.warning(f"Failed to read {fpath}: {e}")
            continue

        if raw_df.empty:
            continue

        symbol = raw_df["symbol"].iloc[0]
        rows = []

        for date_str, group in raw_df.groupby("snapshot_date"):
            spot = group["spot_price"].iloc[0]
            if pd.isna(spot):
                logger.warning(f"{symbol} {date_str}: missing spot price, skipping")
                continue
            factors = deriver.derive_all(group, spot_price=float(spot))
            factors["date"] = date_str
            factors["symbol"] = symbol
            rows.append(factors)

        if rows:
            result = pd.DataFrame(rows)
            result.to_csv(derived_dir / fpath.name, index=False)
            logger.info(f"{symbol}: {len(rows)} dates derived")


def run_pipeline(
    symbols: list[str],
    work_dir: str | Path,
    delay: float = 1.0,
    qlib_dir: str | Path | None = None,
    export_mode: str = "overlay",
):
    """Run the full pipeline: snapshot -> derive -> normalize [-> export-bin].

    Parameters
    ----------
    symbols : list[str]
        Ticker symbols to collect.
    work_dir : str or Path
        Working directory. Creates raw/, derived/, normalized/ subdirs.
    delay : float
        Seconds between API calls.
    qlib_dir : str or Path or None
        If provided, also export to qlib binary format.
    export_mode : str
        'create' or 'overlay' for bin export.
    """
    work_dir = Path(work_dir)
    raw_dir = work_dir / "raw"
    derived_dir = work_dir / "derived"
    normalized_dir = work_dir / "normalized"

    # Stage 1: Snapshot
    logger.info("=== Stage 1: Collecting snapshots ===")
    stats = collect_snapshot(symbols, raw_dir, delay=delay)
    logger.info(f"Collection: {stats}")

    # Stage 2: Derive
    logger.info("=== Stage 2: Deriving factors ===")
    derive_factors(raw_dir, derived_dir)

    # Stage 3: Normalize
    logger.info("=== Stage 3: Normalizing to calendar ===")
    normalize_factors(derived_dir, normalized_dir)

    # Stage 4: Export (optional)
    if qlib_dir:
        logger.info(f"=== Stage 4: Exporting to qlib binary ({export_mode}) ===")
        export_bin(normalized_dir, qlib_dir, mode=export_mode)

    logger.info("Pipeline complete.")
