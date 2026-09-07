#!/usr/bin/env bash
# Gold T Mini hekim brosuru -> PDF (960x540 pt, 16:9)
set -euo pipefail
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
"$CHROME" --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --font-render-hinting=none --no-pdf-header-footer --virtual-time-budget=20000 \
  --print-to-pdf=GoldT_Mini_Hekim_Brosuru_v1.pdf goldt.html
echo "PDF hazir: GoldT_Mini_Hekim_Brosuru_v1.pdf"
