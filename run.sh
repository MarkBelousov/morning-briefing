#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Morning Market Briefing ==="
echo ""

python3 -m pip install -q -r requirements.txt 2>/dev/null || true

echo "Generating briefing..."
python3 briefing.py

echo ""
echo "Sending notifications..."
python3 notify.py

echo ""
echo "Done."
