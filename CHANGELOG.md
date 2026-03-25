# Changelog

All notable changes to **CyberSec News Intelligence** will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] — 2026-03-25

### 📄 Template-Based DOCX Download

#### Added
- **Template Selector** — DOCX download button เปลี่ยนเป็น Split Button พร้อม Dropdown เลือก Template ได้ทั้งในหน้า Modal, Table View, และ Card View
- **XFINIT v1 Template** — Template รายงานสไตล์ XFINIT: header logo, fonts TH Sarabun New, สีชมพู `FF3B63`, sections ครบ 4 ส่วน (สรุปผู้บริหาร / เนื้อหาฉบับเต็ม / การวิเคราะห์ผลกระทบ / คำแนะนำในการรับมือ)
- **`docx_generator_xfinit.py`** — Generator สำหรับ XFINIT v1 ใช้ python-docx + lxml XML manipulation เพื่อ fill article data เข้า template จริง
- **Flask Route `/download-docx/<id>/xfinit`** — Download DOCX ด้วย XFINIT v1 Template

#### Technical Details
- Template file: `assets/xfinit_v1_template.docx` (XFINIT v1 master template)
- Static logo: `static/xfinit_logo.png` (แสดงใน dropdown)
- Generator approach: Copy template → find landmark paragraphs (section headers) → XML-level replacement with lxml
- รองรับ multi-paragraph content, bullet points อัตโนมัติ (`• `), content splitting by newline

---

## [1.1.0] — 2026-03-25

### 🔐 Enterprise Authentication & User Management

#### Added
- **Username + Password Login** — Multi-step login flow: Step 1 username/password → Step 2 TOTP (Google Authenticator)
- **TOTP 2FA (Google Authenticator)** — Time-based One-Time Password ด้วย pyotp, QR Code setup ครั้งแรกผ่าน UI
- **First-Time TOTP Setup** — ผู้ใช้ใหม่จะถูก redirect ไปหน้า Setup Google Authenticator อัตโนมัติ
- **Role-Based Access Control** — บทบาท `admin` และ `user` ควบคุมสิทธิ์การใช้งาน
- **User Management (Admin Only)** — เพิ่ม/ลบ/ระงับผู้ใช้, เปลี่ยน Role, Reset TOTP ผ่าน UI
- **System Configuration (Admin Only)** — ตั้งค่า Server-side API Key, AI Model, SMTP ผ่าน UI
- **Server-side API Key** — เก็บ API Key ใน SQLite `system_config` — ผู้ใช้ทั่วไปไม่ต้องระบุ Key เอง
- **SMTP Configuration** — ตั้งค่า SMTP Server/Port/Username/Password/From สำหรับ Email Alerts
- **Change Password** — ทุก Role เปลี่ยนรหัสผ่านตัวเองได้ผ่านหน้า Settings
- **Default Admin Bootstrap** — สร้าง `admin` / `Admin@1234` อัตโนมัติเมื่อ run ครั้งแรก
- **Login Pages** — หน้า Login สวยงาม cyberpunk style พร้อม Step indicator
- **Session Security** — Session key `authed`, `user_id`, `username`, `role`; pending keys สำหรับ 2FA flow

#### Changed
- **Settings Tab** → แยกเป็น System Configuration (admin only) + Change Password (ทุก user)
- **Translation API** — fallback ใช้ server-side API Key ถ้า client ไม่ได้ส่ง key มา
- **Navbar** — แสดง username, Role badge (Admin), ปุ่ม Logout

#### Technical Details
- New dependencies: `bcrypt>=4.0.0`, `pyotp>=2.9.0`, `qrcode[pil]>=7.4.2`, `Pillow>=10.0.0`
- New DB tables: `users` (id, username, password_hash, totp_secret, role, is_active, totp_verified, created_at, last_login)
- New DB table: `system_config` (key/value pairs)
- New routes: `/login`, `/login/totp`, `/login/setup-totp`, `/logout`
- New API routes: `GET/POST /api/system-config`, `GET/POST /api/users`, `PATCH/DELETE /api/users/<id>`, `POST /api/me/password`

---

## [1.0.0] — 2026-03-25

### 🎉 Initial Release

#### Added
- **URL-based Article Translation** — รับ URL ข่าว Cybersecurity แล้วแปลเป็นภาษาไทยอัตโนมัติ
- **Multi-provider LLM Support** — รองรับ Google Gemini และ OpenRouter (เลือกได้จาก UI)
- **Structured AI Analysis** — แปลพร้อมวิเคราะห์ Thai Title, Summary, Full Content, Impact Analysis, และ Recommendations
- **Severity Classification** — จัดระดับความรุนแรง Critical / High / Medium / Low / Informational อัตโนมัติ
- **Category Tagging** — จัดหมวดหมู่ข่าว เช่น Ransomware, Phishing, Vulnerability, APT ฯลฯ
- **WeasyPrint PDF Generation** — สร้างรายงาน PDF ภาษาไทยคุณภาพสูง พร้อม Thai font (Sarabun)
- **Duplicate URL Detection** — ตรวจจับ URL ซ้ำ แสดง banner พร้อมปุ่ม Download/Preview ทันที
- **Background Async Translation** — ระบบ job queue ด้วย Python threading + polling ทุก 2 วินาที
- **Article History** — เก็บประวัติบทความทั้งหมดใน SQLite พร้อม re-download PDF ได้ตลอด
- **Stars & Tags System** — Starred articles และ custom tags สำหรับจัดการข่าว
- **Card / Table View Toggle** — สลับมุมมองแบบ table และ card grid พร้อม localStorage persistence
- **Copy-to-Clipboard** — ปุ่ม copy แยกต่อ section (Summary, Content, Impact, Recommendations)
- **In-browser PDF Preview** — Preview PDF ใน modal iframe โดยไม่ต้อง download
- **Security Intelligence Dashboard** — กราฟสถิติด้วย Chart.js 4 ประเภท (donut, bar, line, top sources)
- **RSS Auto-Monitor** — จัดการ RSS feeds หลายแหล่ง พร้อม auto-translate บทความใหม่
- **RSS Manual Trigger** — ปุ่ม "รันตอนนี้" สำหรับ fetch RSS ทันที
- **Basic Auth Login** — หน้า login ป้องกันการเข้าถึง (เปิด/ปิดได้ผ่าน config.json)
- **Settings Tab** — ตั้งค่า RSS API, Auth password ผ่าน UI โดยไม่ต้องแก้ไฟล์โดยตรง
- **Cyberpunk UI/UX** — Dark theme, glassmorphism cards, glow effects, gradient branding
- **startup script** — `start.sh` สำหรับติดตั้ง dependencies และเปิด server ในขั้นตอนเดียว
- **`/api/version` endpoint** — ตรวจสอบ version ของ app ได้ผ่าน API

#### Technical Details
- Flask 3.x + SQLite (with fallback path สำหรับ mounted volumes)
- Scraper: trafilatura (primary) → BeautifulSoup4 + lxml (fallback)
- PDF: WeasyPrint (primary) → fpdf2 (fallback)
- Thai font: Sarabun via Google Fonts CSS @import
- Job queue: in-memory dict + threading.Lock()
- Frontend: Vanilla JS, Chart.js 4.4.1, Font Awesome 6.5, Google Fonts

---

## Version Naming Convention

This project uses **Semantic Versioning**: `MAJOR.MINOR.PATCH`

| Type | เมื่อไหร่ | ตัวอย่าง |
|---|---|---|
| `MAJOR` | เปลี่ยน architecture ใหญ่, breaking change | `2.0.0` — ย้ายจาก SQLite → PostgreSQL |
| `MINOR` | เพิ่ม feature ใหม่ backward-compatible | `1.1.0` — เพิ่ม Email notification |
| `PATCH` | แก้ bug, ปรับ UI เล็กน้อย | `1.0.1` — แก้ PDF font issue |

---

[Unreleased]: https://github.com/zildjiean/cybersec-news-intelligence/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/zildjiean/cybersec-news-intelligence/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/zildjiean/cybersec-news-intelligence/releases/tag/v1.0.0
