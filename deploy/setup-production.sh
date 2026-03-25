#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  Production Setup Script — CyberSec News Intelligence
#  รองรับ Ubuntu 20.04 / 22.04 / 24.04
#
#  วิธีใช้:
#    chmod +x setup-production.sh
#    sudo bash setup-production.sh
# ══════════════════════════════════════════════════════════════

set -e

# ── ตัวแปรที่ต้องแก้ไขก่อนรัน ─────────────────────────────────
APP_USER="ubuntu"                                        # user ที่รัน app
APP_DIR="/opt/cybersec-news-intelligence"               # path ติดตั้ง
REPO_URL="https://github.com/zildjiean/cybersec-news-intelligence.git"
DOMAIN="yourdomain.com"                                  # domain หรือ IP ของ server
# ──────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── ตรวจสอบ root ──────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "กรุณารันด้วย sudo: sudo bash $0"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   CyberSec News Intelligence — Production Setup         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── 1. ติดตั้ง system packages ────────────────────────────────
info "ติดตั้ง system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    nginx \
    git \
    curl \
    build-essential \
    libpango-1.0-0 libpangoft2-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 \
    fonts-thai-tlwg

# WeasyPrint system deps (สำหรับ PDF generation)
apt-get install -y -qq \
    libffi-dev libssl-dev \
    python3-cffi python3-brotli \
    2>/dev/null || true

info "System packages ติดตั้งเสร็จ"

# ── 2. Clone / update project ─────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
    info "อัปเดต project จาก GitHub..."
    cd "$APP_DIR"
    sudo -u "$APP_USER" git pull origin main
else
    info "Clone project จาก GitHub..."
    git clone "$REPO_URL" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

# ── 3. Python virtual environment + dependencies ──────────────
info "ตั้งค่า Python virtual environment..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" venv/bin/pip install --upgrade pip -q
sudo -u "$APP_USER" venv/bin/pip install -r requirements.txt -q
sudo -u "$APP_USER" venv/bin/pip install gunicorn -q
info "Python dependencies ติดตั้งเสร็จ"

# ── 4. สร้าง directories ──────────────────────────────────────
info "สร้าง directories..."
mkdir -p /var/log/cybersec-intel
chown "$APP_USER:$APP_USER" /var/log/cybersec-intel

mkdir -p "$APP_DIR/pdfs" "$APP_DIR/fonts"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ── 5. config.json (ถ้ายังไม่มี) ──────────────────────────────
if [ ! -f "$APP_DIR/config.json" ]; then
    warning "ไม่พบ config.json — สร้างจาก template..."
    cp "$APP_DIR/config.example.json" "$APP_DIR/config.json"
    chown "$APP_USER:$APP_USER" "$APP_DIR/config.json"
    warning "กรุณาแก้ไข config.json: nano $APP_DIR/config.json"
fi

# ── 6. ตั้งค่า systemd service ────────────────────────────────
info "ตั้งค่า systemd service..."

# แก้ path ของ gunicorn ให้ใช้ venv
GUNICORN_PATH="$APP_DIR/venv/bin/gunicorn"

cat > /etc/systemd/system/cybersec-intel.service << EOF
[Unit]
Description=CyberSec News Intelligence
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="FLASK_ENV=production"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$GUNICORN_PATH \\
    --workers 4 \\
    --bind 127.0.0.1:5055 \\
    --timeout 120 \\
    --keep-alive 5 \\
    --access-logfile /var/log/cybersec-intel/access.log \\
    --error-logfile /var/log/cybersec-intel/error.log \\
    --log-level info \\
    app:app
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$APP_DIR /var/log/cybersec-intel

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cybersec-intel
systemctl restart cybersec-intel
info "systemd service เปิดใช้งานแล้ว (auto-start เมื่อ reboot)"

# ── 7. ตั้งค่า Nginx ──────────────────────────────────────────
info "ตั้งค่า Nginx..."

cat > /etc/nginx/sites-available/cybersec-intel << EOF
limit_req_zone \$binary_remote_addr zone=cybersec_api:10m rate=30r/m;
limit_req_zone \$binary_remote_addr zone=cybersec_web:10m rate=60r/m;

upstream cybersec_app {
    server 127.0.0.1:5055;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    access_log /var/log/nginx/cybersec-intel.access.log;
    error_log  /var/log/nginx/cybersec-intel.error.log;

    add_header X-Frame-Options        "SAMEORIGIN"    always;
    add_header X-Content-Type-Options "nosniff"       always;
    add_header X-XSS-Protection       "1; mode=block" always;

    client_max_body_size 20M;
    gzip on;
    gzip_types text/plain text/css application/javascript application/json;

    location /static/ {
        alias $APP_DIR/static/;
        expires 7d;
    }

    location /api/ {
        limit_req zone=cybersec_api burst=10 nodelay;
        proxy_pass         http://cybersec_app;
        proxy_http_version 1.1;
        proxy_set_header   Connection      "";
        proxy_set_header   Host            \$host;
        proxy_set_header   X-Real-IP       \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 180s;
    }

    location / {
        limit_req zone=cybersec_web burst=20 nodelay;
        proxy_pass         http://cybersec_app;
        proxy_http_version 1.1;
        proxy_set_header   Connection      "";
        proxy_set_header   Host            \$host;
        proxy_set_header   X-Real-IP       \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

# ลบ default site แล้วเปิด cybersec-intel
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/cybersec-intel /etc/nginx/sites-enabled/

nginx -t && systemctl reload nginx
info "Nginx ตั้งค่าเสร็จแล้ว"

# ── 8. ตรวจสอบ status ─────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
info "ตรวจสอบ service status..."
sleep 2

if systemctl is-active --quiet cybersec-intel; then
    info "cybersec-intel service: RUNNING ✓"
else
    error "cybersec-intel service ไม่ทำงาน — ดู log: journalctl -u cybersec-intel -n 30"
fi

if systemctl is-active --quiet nginx; then
    info "nginx: RUNNING ✓"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ ติดตั้งเสร็จสมบูรณ์!                               ║"
echo "║                                                          ║"
echo "║  🌐 เปิดเบราว์เซอร์: http://$DOMAIN"
echo "║                                                          ║"
echo "║  คำสั่งที่ควรรู้:                                       ║"
echo "║  sudo systemctl status cybersec-intel  → ดู status      ║"
echo "║  sudo journalctl -u cybersec-intel -f  → ดู log live    ║"
echo "║  sudo systemctl restart cybersec-intel → restart app    ║"
echo "║  sudo nginx -t && sudo systemctl reload nginx           ║"
echo "║                                                          ║"
echo "║  ➡ ขั้นตอนต่อไป: ตั้งค่า SSL ด้วย Let's Encrypt       ║"
echo "║  sudo apt install certbot python3-certbot-nginx -y      ║"
echo "║  sudo certbot --nginx -d $DOMAIN"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
