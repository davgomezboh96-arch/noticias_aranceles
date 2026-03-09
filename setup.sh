#!/bin/bash
# setup.sh — Creates directories and installs Python dependencies.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up noticias_aranceles..."

# Create required directories
mkdir -p "$SCRIPT_DIR/output"
mkdir -p "$SCRIPT_DIR/logs"

# Create virtual environment and install dependencies
echo "Creating virtual environment..."
python3 -m venv "$SCRIPT_DIR/.venv"

echo "Installing dependencies..."
"$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

echo ""
echo "✅ Setup complete."
echo "   Run the scraper with: $SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/noticias_aranceles.py"
echo "   Install cron job with: bash $SCRIPT_DIR/install_cron.sh"
