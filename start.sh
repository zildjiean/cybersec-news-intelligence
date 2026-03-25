#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  CyberSec News Intelligence – Startup Script
#  วิธีใช้: bash start.sh
# ══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         CyberSec News Intelligence v1.0                 ║"
echo "║    ระบบแปลข่าว Cybersecurity เป็นภาษาไทย              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Check Python ─────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 ไม่พบในระบบ กรุณาติดตั้ง Python 3.9+"
    exit 1
fi
echo "[✓] Python: $(python3 --version)"

# ── Install / upgrade packages ────────────────────────────────
echo "[...] กำลังติดตั้ง/อัพเดท Python packages..."
pip install -r requirements.txt --break-system-packages -q 2>/dev/null || \
pip install -r requirements.txt -q 2>/dev/null || true

# ── Create directories ─────────────────────────────────────────
mkdir -p pdfs fonts

# ── Download Thai fonts (Sarabun) if not present ──────────────
if [ ! -f "fonts/Sarabun-Regular.ttf" ]; then
    echo "[...] กำลังดาวน์โหลด Thai fonts (Sarabun)..."
    python3 - <<'PYEOF'
import os, sys
try:
    import requests
    font_dir = "fonts"
    os.makedirs(font_dir, exist_ok=True)
    font_urls = {
        "Sarabun-Regular.ttf": "https://fonts.gstatic.com/s/sarabun/v13/DtVmJx26TKEr37c9YK5sulUP.ttf",
        "Sarabun-Bold.ttf":    "https://fonts.gstatic.com/s/sarabun/v13/DtVhJx26TKEr37c9YMQJTuUPpQ.ttf",
    }
    for fname, url in font_urls.items():
        fpath = os.path.join(font_dir, fname)
        if not os.path.exists(fpath):
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            with open(fpath, "wb") as f:
                f.write(r.content)
            print(f"[✓] Downloaded: {fname}")
except Exception as e:
    print(f"[!] Font download skipped (WeasyPrint will be used instead): {e}")
PYEOF
fi

# ── Check if port 5055 is free ────────────────────────────────
if lsof -ti:5055 >/dev/null 2>&1; then
    echo "[!] Port 5055 ถูกใช้งานอยู่ กำลังหยุด process เดิม..."
    lsof -ti:5055 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# ── Start server ───────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🚀 เปิดเบราว์เซอร์ไปที่: http://localhost:5055         ║"
echo "║  กด Ctrl+C เพื่อหยุด server                             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

python3 app.py
