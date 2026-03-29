"""Command-line interface for qlib-options."""

import argparse
import logging
import sys

from qlib_options import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="qlib-options",
        description="Options chain data collection and factor derivation for qlib",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- snapshot ---
    p_snap = subparsers.add_parser("snapshot", help="Collect current options chain snapshots")
    _add_symbol_args(p_snap)
    p_snap.add_argument("--raw-dir", required=True, help="Directory for raw chain CSVs")
    p_snap.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")

    # --- derive ---
    p_derive = subparsers.add_parser("derive", help="Derive factors from raw snapshots")
    p_derive.add_argument("--raw-dir", required=True, help="Directory with raw chain CSVs")
    p_derive.add_argument("--derived-dir", required=True, help="Output directory for derived CSVs")

    # --- normalize ---
    p_norm = subparsers.add_parser("normalize", help="Normalize factors to trading calendar")
    p_norm.add_argument("--derived-dir", required=True, help="Directory with derived CSVs")
    p_norm.add_argument("--normalized-dir", required=True, help="Output directory")

    # --- export-bin ---
    p_bin = subparsers.add_parser("export-bin", help="Export to qlib binary format")
    p_bin.add_argument("--normalized-dir", required=True, help="Directory with normalized CSVs")
    p_bin.add_argument("--qlib-dir", required=True, help="Target qlib data directory")
    p_bin.add_argument(
        "--mode", choices=["create", "overlay"], default="overlay",
        help="'create' for fresh dataset, 'overlay' to augment existing (default: overlay)",
    )

    # --- run ---
    p_run = subparsers.add_parser("run", help="Full pipeline: snapshot -> derive -> normalize")
    _add_symbol_args(p_run)
    p_run.add_argument("--work-dir", required=True, help="Working directory (creates subdirs)")
    p_run.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")
    p_run.add_argument("--qlib-dir", default=None, help="If set, also export to qlib binary")
    p_run.add_argument(
        "--mode", choices=["create", "overlay"], default="overlay",
        help="Export mode (default: overlay)",
    )

    args = parser.parse_args(argv)

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Dispatch
    if args.command == "snapshot":
        from qlib_options.collector import collect_snapshot
        from qlib_options.symbols import load_symbols

        symbols = load_symbols(args.symbols, args.symbols_file)
        stats = collect_snapshot(symbols, args.raw_dir, delay=args.delay)
        print(f"Done: {stats['success']} ok, {stats['failed']} failed, {stats['skipped']} skipped")

    elif args.command == "derive":
        from qlib_options.pipeline import derive_factors

        derive_factors(args.raw_dir, args.derived_dir)

    elif args.command == "normalize":
        from qlib_options.normalize import normalize_factors

        normalize_factors(args.derived_dir, args.normalized_dir)

    elif args.command == "export-bin":
        from qlib_options.qlib_bin import export_bin

        export_bin(args.normalized_dir, args.qlib_dir, mode=args.mode)

    elif args.command == "run":
        from qlib_options.pipeline import run_pipeline
        from qlib_options.symbols import load_symbols

        symbols = load_symbols(args.symbols, args.symbols_file)
        run_pipeline(
            symbols=symbols,
            work_dir=args.work_dir,
            delay=args.delay,
            qlib_dir=args.qlib_dir,
            export_mode=args.mode,
        )


def _add_symbol_args(parser):
    """Add --symbols and --symbols-file args to a subparser."""
    group = parser.add_argument_group("symbol selection")
    group.add_argument(
        "--symbols", default=None,
        help="Comma-separated symbols (e.g., SPY,QQQ,AAPL)",
    )
    group.add_argument(
        "--symbols-file", default=None,
        help="Path to text file with one symbol per line",
    )


if __name__ == "__main__":
    main()
