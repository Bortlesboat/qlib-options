# qlib-options

Options chain data collection and factor derivation, compatible with [Microsoft qlib](https://github.com/microsoft/qlib).

> **Snapshot-only collector.** This tool captures the *current* options chain via Yahoo Finance. It cannot backfill historical data. Run daily (e.g., via cron) to build a time series.

## Install

```bash
pip install qlib-options

# With qlib integration (optional)
pip install qlib-options[qlib]
```

## Quick Start

```bash
# Collect today's snapshot for a few symbols
qlib-options snapshot --symbols SPY,QQQ,AAPL --raw-dir data/raw

# Derive factors from raw chains
qlib-options derive --raw-dir data/raw --derived-dir data/derived

# Normalize to US trading calendar
qlib-options normalize --derived-dir data/derived --normalized-dir data/normalized

# Export to qlib binary format (overlay into existing data)
qlib-options export-bin --normalized-dir data/normalized --qlib-dir ~/.qlib/qlib_data/us_data --mode overlay
```

Or run the full pipeline in one command:

```bash
qlib-options run --symbols SPY,QQQ,AAPL --work-dir data --qlib-dir ~/.qlib/qlib_data/us_data
```

## Factors

| Factor | Column | Description |
|--------|--------|-------------|
| ATM IV (30D) | `atm_iv_30d` | ATM implied volatility interpolated to 30-day tenor |
| Put/Call Ratio (Volume) | `pcr_volume` | Near-term (DTE <= 180) put/call volume ratio |
| Put/Call Ratio (OI) | `pcr_oi` | Near-term (DTE <= 180) put/call open interest ratio |
| Total Open Interest | `total_oi` | Sum of all contract OI |
| Total Volume | `total_volume` | Sum of all contract volume |

## Symbol Universe

By default, uses a curated list of ~30 liquid US names (SPY, QQQ, major tech, sector ETFs). Override with:

```bash
# Explicit list
qlib-options snapshot --symbols SPY,QQQ,AAPL --raw-dir data/raw

# From file (one symbol per line, # comments supported)
qlib-options snapshot --symbols-file my_universe.txt --raw-dir data/raw
```

## Daily Cron Example

```bash
#!/bin/bash
# Run at 4:30 PM ET after market close
cd /path/to/project
qlib-options run --work-dir data --qlib-dir ~/.qlib/qlib_data/us_data --delay 2.0
```

## Using with qlib

Once exported, options factors are available via qlib's standard expression engine:

```python
import qlib
from qlib.data import D

qlib.init(provider_uri="~/.qlib/qlib_data/us_data")

# Access options factors
df = D.features(["SPY"], ["$atm_iv_30d", "$pcr_volume", "$pcr_oi"])

# Use in expressions
df = D.features(["SPY"], [
    "Mean($atm_iv_30d, 20)",      # 20-day MA of ATM IV
    "$pcr_volume / $pcr_oi",       # Volume PCR relative to OI PCR
])
```

## Data Pipeline

```
snapshot (yahooquery) -> raw/ (per-contract CSVs)
                          |
                        derive -> derived/ (per-underlying daily factors)
                                    |
                                normalize -> normalized/ (calendar-aligned)
                                                |
                                            export-bin -> qlib binary features
```

## Limitations

- **No historical backfill** — Yahoo Finance only provides current snapshots
- **US equities only** (v0.1) — NYSE/NASDAQ listed with options
- **Free data quality** — Yahoo data can be stale or missing for illiquid names
- **Snapshot timing matters** — best collected after market close (4 PM ET)

## Related

- [microsoft/qlib#2162](https://github.com/microsoft/qlib/issues/2162) — upstream feature proposal
- [microsoft/qlib](https://github.com/microsoft/qlib) — quantitative investment platform

## License

MIT
