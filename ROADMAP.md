# CyberSec News Intelligence — Enterprise Roadmap

> แผนพัฒนาระบบสู่ระดับ Enterprise สำหรับทีม Security / CISO

---

## ✅ Current State (v1.0)
- Flask + SQLite + WeasyPrint
- Gemini / OpenRouter LLM translation
- Basic Auth (single password)
- RSS Auto-Monitor
- Dashboard (Chart.js)
- Background async job queue (threading)
- Tags, Starred, PDF Preview, Card/Table view
- Cyberpunk glassmorphism UI

---

## Phase 1 — Foundation (Priority: High)

### 🔐 RBAC — Role-Based Access Control
- Roles: `Admin` / `Analyst` / `Viewer`
- Admin: จัดการ users, feeds, settings ทั้งหมด
- Analyst: แปลข่าว, สร้าง PDF, จัดการ tags/starred
- Viewer: ดู dashboard และอ่านรายงานเท่านั้น
- Database: เพิ่ม `users` table พร้อม hashed passwords + role column

### 🐳 Docker + PostgreSQL
- แทนที่ SQLite ด้วย PostgreSQL สำหรับ concurrent users
- `Dockerfile` + `docker-compose.yml` (app + db + redis)
- Environment variables สำหรับ secrets (ไม่ใช้ `config.json`)
- Health check endpoint `/health`

### 📬 Email Notification
- SMTP / SendGrid integration
- Daily/Weekly digest email อัตโนมัติ
- Alert ทันทีเมื่อมีข่าว `Critical` ใหม่
- White-label template ใส่ logo บริษัท

---

## Phase 2 — Intelligence (Priority: Medium)

### 🔌 SSO Integration
- SAML 2.0 / OAuth2 รองรับ Azure AD, Google Workspace, Okta
- เชื่อมต่อ Active Directory ขององค์กร

### ⚡ Celery + Redis Job Queue
- แทนที่ Python `threading` ด้วย Celery workers
- รองรับ concurrent translations หลายชิ้นพร้อมกัน
- Retry logic สำหรับ API failures
- Job history และ monitoring dashboard

### 🤝 Slack / Teams Webhook
- แจ้งเตือน `#security-alerts` channel อัตโนมัติ
- Message card แสดง severity, category, link to article
- Configurable per-severity thresholds

### 🏷️ MITRE ATT&CK Mapping
- Auto-detect Tactics / Techniques ที่กล่าวถึงในข่าว
- Badge แสดง T-code (เช่น T1566 Phishing, T1486 Ransomware)
- Filter บน dashboard ตาม ATT&CK matrix

---

## Phase 3 — Enterprise Integration (Priority: Long-term)

### 📊 Advanced Analytics
- Trend analysis รายสัปดาห์ / รายเดือน
- Threat actor tracking ติดตาม group ที่ปรากฏซ้ำ
- Relevance scoring — ประเมินว่าข่าวกระทบองค์กรของเราแค่ไหน
- CVE enrichment จาก NVD API + VirusTotal IOC lookup

### 📤 Export & Compliance
- STIX 2.1 / TAXII export สำหรับแลกเปลี่ยน threat intel
- White-label PDF ใส่ logo + ชื่อ + เลขเอกสารขององค์กร
- Data Retention Policy — auto-purge ตาม policy
- Audit Log ทุก action พร้อม timestamp + user

### 🔌 REST API & Webhooks
- API Key management สำหรับ system-to-system integration
- `GET /api/v1/articles` พร้อม pagination, filtering
- Webhook notify ระบบภายนอกเมื่อมีบทความใหม่
- OpenAPI / Swagger documentation

### 🛡️ SIEM Integration
- Syslog / CEF format สำหรับ Splunk, IBM QRadar
- Microsoft Sentinel connector
- Elastic SIEM integration

---

## Tech Stack Evolution

| Layer | v1.0 (Current) | Enterprise Target |
|---|---|---|
| Web Framework | Flask | Flask + Gunicorn |
| Database | SQLite | PostgreSQL |
| Job Queue | Python threading | Celery + Redis |
| Auth | Basic Auth | RBAC + SSO (SAML/OAuth2) |
| Deployment | `python app.py` | Docker + docker-compose |
| Notification | — | Email + Slack/Teams |
| Threat Intel | — | MITRE ATT&CK + NVD |
| Export | PDF | PDF + STIX + API |

---

## Quick Wins (สามารถทำได้เร็ว)

1. **White-label PDF** — เพิ่ม logo upload ใน Settings ไม่กี่ชั่วโมง
2. **Email alert** — SMTP integration ~1 วัน
3. **Docker** — Dockerfile พื้นฐาน ~2-3 ชั่วโมง
4. **RBAC** — users table + decorator ~1-2 วัน
5. **Slack webhook** — ไม่กี่ชั่วโมง

---

*อัปเดต: มีนาคม 2026*
