"""Column schemas for raw, derived, and normalized data."""

# Raw chain CSV columns (one row per contract per snapshot)
RAW_COLUMNS = [
    "snapshot_date",
    "snapshot_ts",
    "symbol",
    "spot_price",
    "expiry",
    "strike",
    "option_type",  # C or P
    "bid",
    "ask",
    "last",
    "volume",
    "open_interest",
    "implied_volatility",
    "in_the_money",
    "contract_symbol",
]

# Derived factor CSV columns (one row per symbol per date)
DERIVED_COLUMNS = [
    "date",
    "symbol",
    "atm_iv_30d",
    "pcr_volume",
    "pcr_oi",
    "total_oi",
    "total_volume",
]

# Factor columns only (excludes date/symbol)
FACTOR_COLUMNS = [
    "atm_iv_30d",
    "pcr_volume",
    "pcr_oi",
    "total_oi",
    "total_volume",
]
