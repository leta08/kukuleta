#!/usr/bin/env bash
# Gold T Mini hekim brosuru -> PDF (960x540 pt, 16:9)
set -euo pipefail
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
SRC="${1:-goldt_v2.html}"
OUT="${SRC%.html}.pdf"
"$CHROME" --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --font-render-hinting=none --no-pdf-header-footer --virtual-time-budget=20000 \
  --print-to-pdf="$OUT" "$SRC"
echo "PDF hazir: $OUT"
