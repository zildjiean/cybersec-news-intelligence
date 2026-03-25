"""
PDF Generator – uses WeasyPrint (HTML → PDF) for excellent Thai Unicode support.
Falls back to fpdf2 with a downloaded Thai (Sarabun) font if WeasyPrint fails.
"""
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

# ─── Severity styling ─────────────────────────────────────────────────────────
SEV_STYLES = {
    "Critical": {"bg": "#dc2626", "label": "CRITICAL"},
    "High":     {"bg": "#ea580c", "label": "HIGH"},
    "Medium":   {"bg": "#ca8a04", "label": "MEDIUM"},
    "Low":      {"bg": "#2563eb", "label": "LOW"},
    "Info":     {"bg": "#6b7280", "label": "INFO"},
}

# ─── TLP styling ──────────────────────────────────────────────────────────────
TLP_STYLES = {
    "TLP:CLEAR":        {"bg": "#475569", "label": "TLP:CLEAR"},
    "TLP:GREEN":        {"bg": "#16a34a", "label": "TLP:GREEN"},
    "TLP:AMBER":        {"bg": "#d97706", "label": "TLP:AMBER"},
    "TLP:AMBER+STRICT": {"bg": "#ea580c", "label": "TLP:AMBER+STRICT"},
    "TLP:RED":          {"bg": "#dc2626", "label": "TLP:RED"},
}


def _bullet_to_html(text: str) -> str:
    """Convert bullet-point text (• … or numbered) to HTML <ul><li> list."""
    if not text:
        return "<p>ไม่มีข้อมูล</p>"
    items = []
    for line in text.replace("•", "\n").split("\n"):
        line = line.strip().lstrip("0123456789.-) ").strip()
        if line:
            items.append(f"<li>{line}</li>")
    if items:
        return "<ul>" + "".join(items) + "</ul>"
    return f"<p>{text}</p>"


def _paragraphs_to_html(text: str) -> str:
    """Wrap plain paragraphs in <p> tags."""
    if not text:
        return "<p>ไม่มีข้อมูล</p>"
    parts = [p.strip() for p in text.split("\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in parts) if parts else f"<p>{text}</p>"


def _build_html(article: dict) -> str:
    severity = article.get("severity", "Info")
    sev = SEV_STYLES.get(severity, SEV_STYLES["Info"])
    sev_bg = sev["bg"]
    sev_label = sev["label"]
    tlp_key = article.get("tlp", "TLP:CLEAR") or "TLP:CLEAR"
    tlp = TLP_STYLES.get(tlp_key, TLP_STYLES["TLP:CLEAR"])
    tlp_bg = tlp["bg"]
    tlp_label = tlp["label"]
    category = article.get("category", "ทั่วไป")
    thai_title = article.get("thai_title", "ไม่มีชื่อ")
    source_name = article.get("source_name", "ไม่ทราบ")
    operator = (article.get("operator") or "").strip()
    url = article.get("url", "")
    thai_summary = article.get("thai_summary", "")
    thai_content = article.get("thai_content", "")
    thai_impact = article.get("thai_impact", "")
    thai_recommendation = article.get("thai_recommendation", "")
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Truncate URL for display
    url_display = url if len(url) <= 90 else url[:87] + "..."
    operator_html = f'<strong>ผู้ดำเนินการ:</strong> {operator} &nbsp;|&nbsp;' if operator else ''
    operator_footer = f'ผู้ดำเนินการ: {operator} &nbsp;|&nbsp;' if operator else ''

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Sarabun', 'TH Sarabun New', 'Garuda', Arial, sans-serif;
    font-size: 13pt;
    color: #1a1a2e;
    background: #ffffff;
    line-height: 1.7;
  }}

  /* ── Header ── */
  .page-header {{
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b3e 100%);
    color: white;
    padding: 18px 30px 14px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }}
  .header-left {{ display: flex; align-items: center; gap: 14px; }}
  .header-accent {{
    width: 5px; height: 48px;
    background: #00d4ff;
    border-radius: 3px;
    flex-shrink: 0;
  }}
  .header-title {{
    font-size: 17pt;
    font-weight: 700;
    color: #00d4ff;
    letter-spacing: 1px;
  }}
  .header-sub {{
    font-size: 9pt;
    color: #94a3b8;
    margin-top: 3px;
  }}
  .header-date {{
    font-size: 9pt;
    color: #94a3b8;
    text-align: right;
    padding-top: 4px;
  }}
  .header-date span {{
    color: #00d4ff;
    font-weight: 600;
  }}

  /* ── Badges ── */
  .badge-row {{ padding: 16px 30px 0; display: flex; gap: 10px; }}
  .badge {{
    display: inline-block;
    padding: 4px 14px;
    border-radius: 4px;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: white;
  }}
  .badge-sev {{ background: {sev_bg}; }}
  .badge-cat {{ background: #3b4a6b; }}
  .badge-tlp {{ background: {tlp_bg}; }}

  /* ── Article Title ── */
  .article-title {{
    padding: 14px 30px 8px;
    font-size: 18pt;
    font-weight: 700;
    color: #0a0e1a;
    line-height: 1.4;
  }}

  /* ── Source Info ── */
  .source-info {{
    padding: 6px 30px 14px;
    font-size: 9pt;
    color: #64748b;
    border-bottom: 2px solid #e2e8f0;
    line-height: 1.8;
  }}
  .source-info strong {{ color: #334155; }}
  .source-info a {{ color: #0ea5e9; text-decoration: none; word-break: break-all; }}
  .source-info a:hover {{ text-decoration: underline; }}

  /* ── Section ── */
  .section {{
    padding: 16px 30px 10px;
    page-break-inside: avoid;
  }}
  .section-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1.5px solid currentColor;
  }}
  .section-accent {{
    width: 4px;
    height: 20px;
    border-radius: 2px;
    flex-shrink: 0;
  }}
  .section-title {{
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 0.3px;
  }}

  /* Summary box */
  .summary-box {{
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-left: 5px solid #0ea5e9;
    border-radius: 6px;
    padding: 14px 18px;
    font-size: 12pt;
    color: #0c4a6e;
    line-height: 1.8;
  }}
  .summary-box p {{ margin-bottom: 6px; }}
  .summary-box p:last-child {{ margin-bottom: 0; }}

  /* Content */
  .content-body {{
    font-size: 12pt;
    color: #334155;
    line-height: 1.85;
  }}
  .content-body p {{ margin-bottom: 10px; }}

  /* Impact */
  .impact-box ul {{ padding-left: 0; list-style: none; }}
  .impact-box li {{
    padding: 8px 12px 8px 36px;
    margin-bottom: 6px;
    background: #fff7ed;
    border-left: 4px solid #ea580c;
    border-radius: 4px;
    position: relative;
    font-size: 11.5pt;
    color: #431407;
  }}
  .impact-box li::before {{
    content: "⚠";
    position: absolute;
    left: 10px;
    color: #ea580c;
    font-size: 12pt;
  }}

  /* Recommendations */
  .rec-box ul {{ padding-left: 0; list-style: none; }}
  .rec-box li {{
    padding: 8px 12px 8px 36px;
    margin-bottom: 6px;
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    border-radius: 4px;
    position: relative;
    font-size: 11.5pt;
    color: #14532d;
  }}
  .rec-box li::before {{
    content: "✓";
    position: absolute;
    left: 10px;
    color: #16a34a;
    font-weight: 700;
  }}

  /* ── Footer ── */
  .page-footer {{
    margin-top: 20px;
    background: #0a0e1a;
    color: #94a3b8;
    padding: 10px 30px;
    font-size: 8.5pt;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .page-footer .conf {{ color: #ef4444; font-weight: 600; }}

  @page {{
    size: A4;
    margin: 0;
  }}
  @media print {{
    body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<!-- ── Header ── -->
<div class="page-header">
  <div class="header-left">
    <div class="header-accent"></div>
    <div>
      <div class="header-title">CYBERSEC NEWS INTELLIGENCE</div>
      <div class="header-sub">รายงานข่าวความมั่นคงปลอดภัยไซเบอร์ | สำหรับผู้บริหาร, CISO และทีม Security</div>
    </div>
  </div>
  <div class="header-date">
    วันที่จัดทำ<br/>
    <span>{generated_at}</span>
  </div>
</div>

<!-- ── Badges ── -->
<div class="badge-row">
  <span class="badge badge-sev">{sev_label}</span>
  <span class="badge badge-cat">{category}</span>
  <span class="badge badge-tlp">{tlp_label}</span>
</div>

<!-- ── Title ── -->
<div class="article-title">{thai_title}</div>

<!-- ── Source ── -->
<div class="source-info">
  {operator_html}<strong>แหล่งที่มา:</strong> {source_name}<br/>
  <strong>Reference:</strong> <a href="{url}">{url_display}</a>
</div>

<!-- ── Executive Summary ── -->
<div class="section">
  <div class="section-header" style="color: #0ea5e9; border-color: #0ea5e9;">
    <div class="section-accent" style="background:#0ea5e9;"></div>
    <div class="section-title">สรุปสำหรับผู้บริหาร (Executive Summary)</div>
  </div>
  <div class="summary-box">
    {_paragraphs_to_html(thai_summary)}
  </div>
</div>

<!-- ── Full Content ── -->
<div class="section">
  <div class="section-header" style="color: #7c3aed; border-color: #7c3aed;">
    <div class="section-accent" style="background:#7c3aed;"></div>
    <div class="section-title">เนื้อหาฉบับเต็ม (ภาษาไทย)</div>
  </div>
  <div class="content-body">
    {_paragraphs_to_html(thai_content)}
  </div>
</div>

<!-- ── Impact Analysis ── -->
<div class="section impact-box">
  <div class="section-header" style="color: #ea580c; border-color: #ea580c;">
    <div class="section-accent" style="background:#ea580c;"></div>
    <div class="section-title">การวิเคราะห์ผลกระทบต่อองค์กร</div>
  </div>
  {_bullet_to_html(thai_impact)}
</div>

<!-- ── Recommendations ── -->
<div class="section rec-box">
  <div class="section-header" style="color: #16a34a; border-color: #16a34a;">
    <div class="section-accent" style="background:#16a34a;"></div>
    <div class="section-title">คำแนะนำในการรับมือและป้องกัน</div>
  </div>
  {_bullet_to_html(thai_recommendation)}
</div>

<!-- ── Footer ── -->
<div class="page-footer">
  <div>
    {operator_footer}จัดทำโดยระบบ CyberSec News Intelligence &nbsp;|&nbsp;
    <span class="conf">CONFIDENTIAL</span> – สำหรับใช้ภายในองค์กรเท่านั้น
  </div>
  <div>วันที่: {generated_at}</div>
</div>

</body>
</html>"""


def generate_pdf(article: dict, output_path: str) -> bool:
    """
    Generate a professional Thai PDF report from translated article data.
    Uses WeasyPrint (HTML→PDF) which has excellent Thai Unicode support.
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    html_content = _build_html(article)

    # ── Strategy 1: WeasyPrint ────────────────────────────────────────────────
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        font_config = FontConfiguration()
        HTML(string=html_content).write_pdf(
            output_path,
            font_config=font_config,
            presentational_hints=True,
        )
        print(f"[PDF] Generated via WeasyPrint: {output_path}")
        return True
    except Exception as e:
        print(f"[PDF] WeasyPrint failed: {e}, trying fpdf2 fallback...")

    # ── Strategy 2: fpdf2 + Sarabun font (if available) ──────────────────────
    try:
        from fpdf import FPDF

        regular = os.path.join(FONT_DIR, "Sarabun-Regular.ttf")
        bold_f = os.path.join(FONT_DIR, "Sarabun-Bold.ttf")

        # Try to download fonts if missing
        if not os.path.exists(regular):
            _try_download_fonts()

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.set_margins(20, 20, 20)
        pdf.add_page()

        if os.path.exists(regular) and os.path.getsize(regular) > 1000:
            pdf.add_font("Sarabun", "", regular)
            # Use regular as bold fallback if bold font is missing/empty
            bold_src = bold_f if (os.path.exists(bold_f) and os.path.getsize(bold_f) > 1000) else regular
            pdf.add_font("Sarabun", "B", bold_src)
            font_name = "Sarabun"
        else:
            font_name = "Helvetica"

        # Header
        pdf.set_fill_color(10, 14, 26)
        pdf.rect(0, 0, 210, 25, "F")
        pdf.set_font(font_name, "B", 13)
        pdf.set_text_color(0, 212, 255)
        pdf.set_xy(15, 8)
        pdf.cell(0, 7, "CYBERSEC NEWS INTELLIGENCE")
        pdf.set_font(font_name, "", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.set_xy(15, 17)
        pdf.cell(0, 5, "รายงานข่าวความมั่นคงปลอดภัยไซเบอร์")
        pdf.ln(20)

        # Operator + Source + URL
        _op = article.get("operator", "").strip()
        _url = article.get("url", "")
        _src = article.get("source_name", "")
        pdf.set_font(font_name, "", 9)
        pdf.set_text_color(100, 116, 139)
        if _op:
            pdf.cell(0, 5, f"ผู้ดำเนินการ: {_op}", ln=True)
        if _src:
            pdf.cell(0, 5, f"แหล่งที่มา: {_src}", ln=True)
        if _url:
            _url_short = _url if len(_url) <= 90 else _url[:87] + "..."
            pdf.cell(0, 5, f"Reference: {_url_short}", ln=True)
        pdf.ln(3)

        # Title
        pdf.set_font(font_name, "B", 15)
        pdf.set_text_color(10, 14, 26)
        pdf.multi_cell(0, 9, article.get("thai_title", ""))
        pdf.ln(4)

        # Summary
        pdf.set_font(font_name, "B", 11)
        pdf.set_text_color(14, 165, 233)
        pdf.cell(0, 7, "สรุปสำหรับผู้บริหาร", ln=True)
        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(30, 50, 80)
        pdf.multi_cell(0, 6, article.get("thai_summary", ""))
        pdf.ln(4)

        # Content
        pdf.set_font(font_name, "B", 11)
        pdf.set_text_color(124, 58, 237)
        pdf.cell(0, 7, "เนื้อหาฉบับเต็ม", ln=True)
        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, article.get("thai_content", ""))
        pdf.ln(4)

        # Impact
        pdf.set_font(font_name, "B", 11)
        pdf.set_text_color(234, 88, 12)
        pdf.cell(0, 7, "การวิเคราะห์ผลกระทบ", ln=True)
        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, article.get("thai_impact", ""))
        pdf.ln(4)

        # Recommendations
        pdf.set_font(font_name, "B", 11)
        pdf.set_text_color(22, 163, 74)
        pdf.cell(0, 7, "คำแนะนำในการรับมือ", ln=True)
        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, article.get("thai_recommendation", ""))

        pdf.output(output_path)
        print(f"[PDF] Generated via fpdf2: {output_path}")
        return True

    except Exception as e2:
        print(f"[PDF] fpdf2 also failed: {e2}")
        return False


def _try_download_fonts():
    """Attempt to download Sarabun fonts from Google Fonts (requires internet)."""
    import requests as req
    os.makedirs(FONT_DIR, exist_ok=True)
    font_urls = {
        "Sarabun-Regular.ttf": "https://fonts.gstatic.com/s/sarabun/v13/DtVmJx26TKEr37c9YK5sulUP.ttf",
        "Sarabun-Bold.ttf":    "https://fonts.gstatic.com/s/sarabun/v13/DtVhJx26TKEr37c9YMQJTuUPpQ.ttf",
    }
    for fname, url in font_urls.items():
        fpath = os.path.join(FONT_DIR, fname)
        if not os.path.exists(fpath):
            try:
                r = req.get(url, timeout=15)
                r.raise_for_status()
                with open(fpath, "wb") as f:
                    f.write(r.content)
                print(f"[PDF] Font downloaded: {fname}")
            except Exception as e:
                print(f"[PDF] Font download failed ({fname}): {e}")
