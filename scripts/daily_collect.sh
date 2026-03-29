#!/usr/bin/env bash
# daily_collect.sh — Collect end-of-day options snapshots via qlib-options.
# Designed for Windows Task Scheduler (Git Bash) or Linux cron.
# Usage: bash daily_collect.sh

set -euo pipefail

WORK_DIR="${QLIB_OPTIONS_DATA_DIR:-$HOME/qlib-options-data}"
LOG_DIR="$WORK_DIR/logs"
LOG_FILE="$LOG_DIR/collect_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

echo "=== qlib-options daily collect ===" | tee "$LOG_FILE"
echo "Start: $(date -Iseconds)"          | tee -a "$LOG_FILE"
echo "Work dir: $WORK_DIR"               | tee -a "$LOG_FILE"

# Activate venv if one exists next to this script's repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
if [[ -f "$REPO_DIR/.venv/Scripts/activate" ]]; then
    # Windows venv (Git Bash)
    source "$REPO_DIR/.venv/Scripts/activate"
elif [[ -f "$REPO_DIR/.venv/bin/activate" ]]; then
    # Linux/macOS venv
    source "$REPO_DIR/.venv/bin/activate"
fi

# Run the collection pipeline (default 30-symbol universe, 2s delay between tickers)
if qlib-options run --work-dir "$WORK_DIR" --delay 2.0 -v >> "$LOG_FILE" 2>&1; then
    echo "Success: $(date -Iseconds)" | tee -a "$LOG_FILE"
else
    EXIT_CODE=$?
    echo "FAILED (exit $EXIT_CODE): $(date -Iseconds)" | tee -a "$LOG_FILE"
    exit $EXIT_CODE
fi

# Prune logs older than 30 days
find "$LOG_DIR" -name "collect_*.log" -mtime +30 -delete 2>/dev/null || true

echo "Done: $(date -Iseconds)" | tee -a "$LOG_FILE"
