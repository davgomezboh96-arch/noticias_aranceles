#!/bin/bash
# install_cron.sh — Installs a daily cron job for the tariff news scraper.
#
# Why absolute paths?
# cron runs in a minimal environment with no PATH, no .bashrc, and no shell
# variables. Always use full paths for both the interpreter and the script.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python"
SCRIPT_PATH="$SCRIPT_DIR/noticias_aranceles.py"
LOG_PATH="$SCRIPT_DIR/logs/cron.log"

# Ensure the main script exists before installing the cron job
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: Script not found at $SCRIPT_PATH"
    exit 1
fi

# Ensure the logs directory exists (cron won't create it)
mkdir -p "$SCRIPT_DIR/logs"

# The cron entry: runs every day at 7:00 AM
CRON_JOB="0 7 * * * $PYTHON_PATH $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Avoid adding a duplicate if the cron job already exists
if crontab -l 2>/dev/null | grep -F "$SCRIPT_PATH" > /dev/null; then
    echo "⚠  Cron job already exists. No duplicate added."
    echo "   Current entry:"
    crontab -l | grep -F "$SCRIPT_PATH"
    exit 0
fi

# Add the cron job:
# 1. crontab -l  — lists existing entries (2>/dev/null handles empty crontab)
# 2. echo ...    — appends our new entry
# 3. | crontab - — writes the result back as the new crontab
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron job installed successfully."
echo ""
echo "   Schedule : Every day at 7:00 AM"
echo "   Script   : $SCRIPT_PATH"
echo "   Log      : $LOG_PATH"
echo ""
echo "   Useful commands:"
echo "     crontab -l       → view your cron jobs"
echo "     crontab -e       → edit your cron jobs"
echo "     tail -f $LOG_PATH  → follow the cron log"
