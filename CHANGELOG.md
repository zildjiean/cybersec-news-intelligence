# Changelog

All notable changes to **CyberSec News Intelligence** will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]
> Features planned but not yet released — see [ROADMAP.md](ROADMAP.md)

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

[Unreleased]: https://github.com/zildjiean/cybersec-news-intelligence/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/zildjiean/cybersec-news-intelligence/releases/tag/v1.0.0
