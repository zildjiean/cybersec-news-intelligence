import json
import re
import requests

# ─── API Endpoints ────────────────────────────────────────────────────────────
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OR_MODEL = "google/gemini-2.0-flash-001"

# ─── Translation Prompt ───────────────────────────────────────────────────────
PROMPT_TEMPLATE = """คุณเป็นผู้เชี่ยวชาญด้าน Cybersecurity ระดับอาวุโสที่มีความเชี่ยวชาญในการวิเคราะห์ข่าวภัยคุกคามและแปลเป็นภาษาไทยสำหรับผู้บริหาร, CISO, และทีม Security Engineer

กรุณาแปลและวิเคราะห์ข่าวต่อไปนี้ แล้วตอบกลับเป็น JSON เท่านั้น (ไม่มีข้อความอื่น):

ชื่อเรื่อง: {title}
แหล่งที่มา: {source}
เนื้อหา:
{content}

ตอบในรูปแบบ JSON ดังนี้:
{{
    "thai_title": "ชื่อเรื่องภาษาไทยที่กระชับ สื่อความหมายชัดเจน ไม่เกิน 120 ตัวอักษร",
    "thai_summary": "สรุปสำหรับผู้บริหาร (Executive Summary) 4-6 ประโยค อธิบายว่าเกิดอะไรขึ้น ใครได้รับผลกระทบ และเหตุใดจึงสำคัญ เขียนภาษาไทยที่เข้าใจง่ายสำหรับผู้บริหารที่ไม่ใช่ผู้เชี่ยวชาญด้านเทคนิค",
    "thai_content": "แปลเนื้อหาทั้งหมดเป็นภาษาไทยอย่างละเอียด รักษาคำศัพท์ทางเทคนิคที่สำคัญโดยใส่ภาษาอังกฤษในวงเล็บ เช่น ช่องโหว่ (Vulnerability), มัลแวร์ (Malware)",
    "thai_impact": "วิเคราะห์ผลกระทบต่อองค์กร 3-5 ข้อ แต่ละข้อขึ้นต้นด้วย • แยกบรรทัด ครอบคลุม: ผลกระทบด้านการดำเนินงาน, ความเสี่ยงข้อมูล, ด้านการเงิน, ชื่อเสียง และด้านกฎหมาย/กฎระเบียบ",
    "thai_recommendation": "คำแนะนำการรับมือและป้องกัน 4-6 ข้อ แต่ละข้อขึ้นต้นด้วย • แยกบรรทัด เป็นขั้นตอนที่ปฏิบัติได้จริงสำหรับทีม Security",
    "severity": "ระดับความรุนแรง เลือกหนึ่ง: Critical, High, Medium, Low, Info",
    "category": "หมวดหมู่ เลือกหนึ่ง: Ransomware, Phishing, Vulnerability/CVE, Data Breach, Malware, APT/Threat Actor, Supply Chain Attack, Social Engineering, Policy/Regulation, Cloud Security, IoT Security, ทั่วไป"
}}"""


# ─── API Callers ──────────────────────────────────────────────────────────────

def call_gemini(prompt: str, api_key: str, model: str) -> str:
    url = GEMINI_URL.format(model=model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        },
    }
    resp = requests.post(
        url, json=payload, params={"key": api_key},
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_openrouter(prompt: str, api_key: str, model: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://cybersec-intel.local",
        "X-Title": "CyberSec News Intelligence",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 8192,
    }
    resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ─── Response Parser ──────────────────────────────────────────────────────────

def parse_json_response(text: str) -> dict:
    # Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract from markdown code block
    for pattern in [r'```json\s*([\s\S]*?)\s*```', r'```\s*([\s\S]*?)\s*```']:
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass

    # Extract raw JSON object
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    return {}


# ─── Main Entry Point ─────────────────────────────────────────────────────────

DEFAULTS = {
    "thai_title": "",
    "thai_summary": "ไม่สามารถสรุปได้",
    "thai_content": "",
    "thai_impact": "• ไม่สามารถวิเคราะห์ผลกระทบได้",
    "thai_recommendation": "• ไม่สามารถให้คำแนะนำได้",
    "severity": "Info",
    "category": "ทั่วไป",
}


def translate_article(article_data: dict, api_key: str,
                       api_type: str = "gemini", model: str = "") -> dict | None:
    title = article_data.get("title", "ไม่มีชื่อเรื่อง")
    content = article_data.get("content", "")[:9000]
    source = article_data.get("source", "ไม่ทราบแหล่งที่มา")

    prompt = PROMPT_TEMPLATE.format(
        title=title, source=source, content=content
    )

    try:
        if api_type == "gemini":
            raw = call_gemini(prompt, api_key, model or DEFAULT_GEMINI_MODEL)
        else:
            raw = call_openrouter(prompt, api_key, model or DEFAULT_OR_MODEL)

        result = parse_json_response(raw)

        # Fill missing fields with defaults
        for key, default in DEFAULTS.items():
            if not result.get(key):
                result[key] = default if key != "thai_title" else title

        print(f"[Translator] Done. Severity={result['severity']} Category={result['category']}")
        return result

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 0
        if status == 400:
            raise ValueError("API Key ไม่ถูกต้อง หรือ Model ไม่รองรับ")
        elif status == 429:
            raise ValueError("เกิน Quota หรือ Rate Limit ของ API กรุณารอสักครู่แล้วลองใหม่")
        elif status == 403:
            raise ValueError("API Key ไม่มีสิทธิ์เข้าถึง กรุณาตรวจสอบ API Key")
        else:
            raise ValueError(f"API Error: HTTP {status}")
    except Exception as e:
        print(f"[Translator] Error: {e}")
        raise
