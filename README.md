# 🛡️ CyberSec News Intelligence

ระบบแปลข่าวความมั่นคงปลอดภัยไซเบอร์เป็นภาษาไทย
พร้อมสร้างรายงาน PDF สำหรับผู้บริหาร, CISO และทีม Security

---

## 🚀 วิธีเริ่มต้นใช้งาน

```bash
# วิธีที่ 1 (แนะนำ) – ใช้ startup script
bash start.sh

# วิธีที่ 2 – รันตรง
pip install -r requirements.txt
python3 app.py
```

เปิดเบราว์เซอร์ไปที่: **http://localhost:5055**

---

## ⚙️ การตั้งค่า

1. คลิก **"ตั้งค่า API / Model"** ในหน้าเว็บ
2. เลือกผู้ให้บริการ: **Google Gemini** หรือ **OpenRouter**
3. วาง **API Key** ของคุณ
4. เลือก **โมเดล AI** ที่ต้องการ
5. คลิก **"บันทึกการตั้งค่า"** (บันทึกในเบราว์เซอร์ ไม่ส่งออกไปที่ใด)

### วิธีขอ API Key

| ผู้ให้บริการ | URL |
|---|---|
| Google Gemini | https://aistudio.google.com/app/apikey |
| OpenRouter | https://openrouter.ai/keys |

---

## ✨ ฟีเจอร์หลัก

- **แปลข่าวอัตโนมัติ** – ดึงเนื้อหาจาก URL และแปลเป็นภาษาไทย
- **วิเคราะห์ AI** – Executive Summary, Impact Analysis, Recommendations
- **จัดระดับความรุนแรง** – Critical / High / Medium / Low / Info
- **หมวดหมู่อัตโนมัติ** – Ransomware, CVE, Data Breach, etc.
- **PDF อย่างเป็นทางการ** – รูปแบบรายงาน สำหรับส่งผู้บริหาร/CISO
- **ตรวจจับ URL ซ้ำ** – แจ้งเตือนพร้อมปุ่ม Download PDF เดิม
- **ประวัติการแปล** – บันทึกทุกบทความ ค้นหาและ Download ซ้ำได้

---

## 📁 โครงสร้างไฟล์

```
CybersecNews-PDF/
├── app.py            # Flask backend
├── database.py       # SQLite database
├── scraper.py        # Web content extraction
├── translator.py     # Gemini / OpenRouter API
├── pdf_generator.py  # PDF creation (WeasyPrint)
├── templates/
│   └── index.html    # Frontend UI
├── pdfs/             # ไฟล์ PDF ที่สร้างแล้ว
├── fonts/            # Thai fonts (ดาวน์โหลดอัตโนมัติ)
├── cybersec_news.db  # SQLite database
├── requirements.txt
└── start.sh
```
