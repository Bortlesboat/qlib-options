#!/bin/bash
# Daily options snapshot collection — run via cron at 4:30 PM ET
#
# crontab -e:
#   30 16 * * 1-5 /path/to/cron_daily.sh >> /var/log/qlib-options.log 2>&1

set -e

WORK_DIR="${HOME}/qlib-options-data"
QLIB_DIR="${HOME}/.qlib/qlib_data/us_data"

qlib-options run \
    --work-dir "${WORK_DIR}" \
    --qlib-dir "${QLIB_DIR}" \
    --delay 2.0

echo "$(date): Snapshot complete"
