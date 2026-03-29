"""Symbol universe management."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Packaged default universe: liquid US options names
_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_UNIVERSE = _DATA_DIR / "us_liquid_options.txt"


def load_symbols(symbols_arg=None, symbols_file=None):
    """Resolve symbol list from CLI arguments.

    Priority: explicit --symbols > --symbols-file > packaged default universe.

    Parameters
    ----------
    symbols_arg : str or None
        Comma-separated symbol list (e.g., "SPY,QQQ,AAPL").
    symbols_file : str or None
        Path to a text file with one symbol per line.

    Returns
    -------
    list[str]
        Sorted, deduplicated, uppercased symbols.
    """
    if symbols_arg:
        raw = [s.strip().upper() for s in symbols_arg.split(",") if s.strip()]
    elif symbols_file:
        path = Path(symbols_file)
        if not path.exists():
            raise FileNotFoundError(f"Symbols file not found: {path}")
        raw = [
            line.strip().upper()
            for line in path.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    elif _DEFAULT_UNIVERSE.exists():
        raw = [
            line.strip().upper()
            for line in _DEFAULT_UNIVERSE.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        logger.info(f"Using packaged universe: {len(raw)} symbols")
    else:
        raise ValueError("No symbols specified. Use --symbols or --symbols-file.")

    return sorted(set(raw))
