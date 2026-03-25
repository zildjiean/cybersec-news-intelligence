"""
CyberSec News Intelligence – Flask Application
แปลข่าว Cybersecurity เป็นภาษาไทย และสร้างรายงาน PDF สำหรับผู้บริหาร / CISO
"""
import os, re, json, uuid, threading
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, jsonify,
                   send_file, session, redirect, url_for)

from database import Database
from scraper import scrape_article
from translator import translate_article
from pdf_generator import generate_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR  = os.path.join(BASE_DIR, 'pdfs')
os.makedirs(PDF_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── DB (with fallback) ──────────────────────────────────────────────────────
_DB_PRIMARY  = os.path.join(BASE_DIR, 'cybersec_news.db')
_DB_FALLBACK = os.path.join(os.path.expanduser('~'), 'cybersec_news.db')
try:
    db = Database(_DB_PRIMARY)
    import sqlite3 as _sq; _sq.connect(_DB_PRIMARY).close()
except Exception:
    db = Database(_DB_FALLBACK)

# ── Config ──────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg: dict):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ── In-memory job queue ─────────────────────────────────────────────────────
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

def _set_job(jid, **kw):
    with _jobs_lock:
        if jid not in _jobs:
            _jobs[jid] = {}
        _jobs[jid].update(kw)

def _get_job(jid):
    with _jobs_lock:
        return dict(_jobs.get(jid, {}))

# ── Auth middleware ─────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        cfg = load_config()
        if cfg.get('auth_enabled') and not session.get('authed'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

# ── Helpers ─────────────────────────────────────────────────────────────────
def safe_filename(title: str, aid: int) -> str:
    safe = re.sub(r'[^\w\u0E00-\u0E7F\-]', '_', title)[:40]
    ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'cybersec_{aid}_{ts}.pdf'

# ════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    cfg = load_config()
    if not cfg.get('auth_enabled'):
        return redirect(url_for('index'))
    err = None
    if request.method == 'POST':
        pw = request.form.get('password', '')
        if pw == cfg.get('auth_password', 'cybersec2024'):
            session['authed'] = True
            return redirect(url_for('index'))
        err = 'รหัสผ่านไม่ถูกต้อง'
    return render_template('login.html', error=err)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ════════════════════════════════════════════════════════════════════════════
#  MAIN PAGE
# ════════════════════════════════════════════════════════════════════════════

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# ════════════════════════════════════════════════════════════════════════════
#  TRANSLATION (async background job)
# ════════════════════════════════════════════════════════════════════════════

def _translation_worker(jid, url, api_key, api_type, model):
    try:
        _set_job(jid, status='scraping', progress=10, step='ดึงเนื้อหาจากเว็บไซต์')
        article_data = scrape_article(url)
        if not article_data or len(article_data.get('content', '')) < 80:
            _set_job(jid, status='error',
                     error='ไม่สามารถดึงเนื้อหาจาก URL ได้ อาจเป็นเพราะเว็บไซต์มีการป้องกัน')
            return

        _set_job(jid, status='translating', progress=40, step='กำลังแปลด้วย AI')
        translated = translate_article(article_data, api_key, api_type, model)
        if not translated:
            _set_job(jid, status='error', error='ไม่สามารถแปลบทความได้')
            return

        translated['source_name'] = article_data.get('source', '')
        translated['url']         = url

        _set_job(jid, status='saving', progress=75, step='บันทึกข้อมูล')
        pdf_name = f'cybersec_tmp_{jid[:8]}.pdf'
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        aid = db.save_article({
            'url': url,
            'original_title':    article_data.get('title', ''),
            'thai_title':        translated['thai_title'],
            'original_content':  article_data.get('content', '')[:6000],
            'thai_content':      translated['thai_content'],
            'thai_summary':      translated['thai_summary'],
            'thai_impact':       translated['thai_impact'],
            'thai_recommendation': translated['thai_recommendation'],
            'source_name':       article_data.get('source', ''),
            'severity':          translated['severity'],
            'category':          translated['category'],
            'pdf_path':          pdf_path,
            'pdf_filename':      pdf_name,
        })

        # Rename with real ID
        final_name = safe_filename(translated['thai_title'], aid)
        final_path = os.path.join(PDF_DIR, final_name)

        _set_job(jid, status='pdf', progress=88, step='สร้างรายงาน PDF')
        pdf_ok = generate_pdf(translated, final_path)

        if pdf_ok and os.path.exists(final_path):
            import sqlite3
            c = sqlite3.connect(db.db_path)
            c.execute('UPDATE articles SET pdf_path=?,pdf_filename=? WHERE id=?',
                      (final_path, final_name, aid))
            c.commit(); c.close()
            if os.path.exists(pdf_path) and pdf_path != final_path:
                try: os.remove(pdf_path)
                except: pass

        _set_job(jid, status='done', progress=100, step='เสร็จสิ้น',
                 article_id=aid,
                 thai_title=translated['thai_title'],
                 thai_summary=translated['thai_summary'],
                 severity=translated['severity'],
                 category=translated['category'],
                 pdf_ready=pdf_ok)

    except Exception as e:
        _set_job(jid, status='error', error=str(e))

@app.route('/api/translate', methods=['POST'])
@login_required
def start_translate():
    data     = request.get_json(silent=True) or {}
    url      = (data.get('url') or '').strip()
    api_key  = (data.get('api_key') or '').strip()
    api_type = (data.get('api_type') or 'gemini').lower()
    model    = (data.get('model') or '').strip()

    if not url:    return jsonify({'error': 'กรุณาระบุ URL'}), 400
    if not api_key: return jsonify({'error': 'กรุณาระบุ API Key'}), 400

    existing = db.get_article_by_url(url)
    if existing:
        return jsonify({
            'duplicate': True,
            'article_id': existing['id'],
            'thai_title': existing['thai_title'],
            'severity':   existing['severity'],
            'category':   existing['category'],
        })

    jid = str(uuid.uuid4())
    _set_job(jid, status='pending', progress=0, step='เริ่มต้น', url=url)
    t = threading.Thread(target=_translation_worker,
                         args=(jid, url, api_key, api_type, model), daemon=True)
    t.start()
    return jsonify({'job_id': jid})

@app.route('/api/job/<jid>')
@login_required
def poll_job(jid):
    job = _get_job(jid)
    if not job:
        return jsonify({'status': 'not_found'}), 404
    return jsonify(job)

# ════════════════════════════════════════════════════════════════════════════
#  DUPLICATE CHECK
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/check-url', methods=['POST'])
@login_required
def check_url():
    data = request.get_json(silent=True) or {}
    url  = (data.get('url') or '').strip()
    if not url: return jsonify({'error': 'กรุณาระบุ URL'}), 400
    existing = db.get_article_by_url(url)
    if existing:
        return jsonify({'exists': True, 'article': {
            'id': existing['id'], 'thai_title': existing['thai_title'],
            'severity': existing['severity'], 'category': existing['category'],
            'created_at': existing['created_at'],
        }})
    return jsonify({'exists': False})

# ════════════════════════════════════════════════════════════════════════════
#  ARTICLES
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/history')
@login_required
def history():
    q = request.args.get('q', '').strip()
    arts = db.search_articles(q) if q else db.get_all_articles()
    return jsonify(arts)

@app.route('/api/article/<int:aid>')
@login_required
def get_article(aid):
    a = db.get_article_by_id(aid)
    if not a: return jsonify({'error': 'ไม่พบบทความ'}), 404
    return jsonify(a)

@app.route('/api/article/<int:aid>', methods=['PATCH'])
@login_required
def patch_article(aid):
    data = request.get_json(silent=True) or {}
    if 'starred' in data:
        db.update_starred(aid, data['starred'])
    if 'tags' in data:
        db.update_tags(aid, str(data['tags']))
    meta_keys = ('thai_title', 'severity', 'tlp', 'operator')
    if any(k in data for k in meta_keys):
        db.update_article_meta(
            aid,
            thai_title=data.get('thai_title'),
            severity=data.get('severity'),
            tlp=data.get('tlp'),
            operator=data.get('operator'),
        )
    return jsonify({'success': True})

@app.route('/api/article/<int:aid>', methods=['DELETE'])
@login_required
def delete_article(aid):
    a = db.get_article_by_id(aid)
    if a:
        pdf = a.get('pdf_path') or ''
        if pdf and os.path.exists(pdf):
            try: os.remove(pdf)
            except: pass
        db.delete_article(aid)
    return jsonify({'success': True})

# ── PDF Download & Preview ──────────────────────────────────────────────────

def _ensure_pdf(aid: int) -> str | None:
    a = db.get_article_by_id(aid)
    if not a: return None
    pdf = a.get('pdf_path') or ''
    if pdf and os.path.exists(pdf):
        return pdf
    # Re-generate
    translated = {k: a.get(k, '') for k in (
        'thai_title','thai_summary','thai_content',
        'thai_impact','thai_recommendation','severity',
        'category','source_name','url','tlp','operator')}
    regen = os.path.join(PDF_DIR, f'cybersec_{aid}_regen.pdf')
    ok = generate_pdf(translated, regen)
    return regen if ok else None

@app.route('/preview/<int:aid>')
@login_required
def preview_pdf(aid):
    pdf = _ensure_pdf(aid)
    if not pdf: return 'ไม่สามารถสร้าง PDF ได้', 500
    return send_file(pdf, as_attachment=False, mimetype='application/pdf')

@app.route('/download-docx/<int:aid>')
@login_required
def download_docx(aid):
    a = db.get_article_by_id(aid)
    if not a: return 'ไม่พบบทความ', 404
    from docx_generator import generate_docx, DOCX_AVAILABLE
    if not DOCX_AVAILABLE:
        return 'ต้องติดตั้ง python-docx: pip install python-docx', 500
    translated = {k: a.get(k, '') for k in (
        'thai_title', 'thai_summary', 'thai_content', 'thai_impact',
        'thai_recommendation', 'severity', 'category', 'source_name',
        'url', 'tlp', 'operator')}
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    docx_path = os.path.join(PDF_DIR, f'cybersec_{aid}_{ts}.docx')
    ok = generate_docx(translated, docx_path)
    if not ok: return 'ไม่สามารถสร้าง DOCX ได้', 500
    dl_name = re.sub(r'[^\w\u0E00-\u0E7F\-.]', '_',
                     f'CyberSecNews_{aid}_{a["thai_title"][:20]}.docx')
    return send_file(docx_path, as_attachment=True, download_name=dl_name,
                     mimetype='application/vnd.openxmlformats-officedocument'
                               '.wordprocessingml.document')

@app.route('/download/<int:aid>')
@login_required
def download_pdf(aid):
    a = db.get_article_by_id(aid)
    if not a: return 'ไม่พบบทความ', 404
    pdf = _ensure_pdf(aid)
    if not pdf: return 'ไม่สามารถสร้าง PDF ได้', 500
    name = re.sub(r'[^\w\u0E00-\u0E7F\-.]', '_',
                  f'CyberSecNews_{aid}_{a["thai_title"][:20]}.pdf')
    return send_file(pdf, as_attachment=True, download_name=name)

# ════════════════════════════════════════════════════════════════════════════
#  STATS / DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/stats')
@login_required
def stats():
    return jsonify(db.get_stats())

# ════════════════════════════════════════════════════════════════════════════
#  RSS FEEDS
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/rss', methods=['GET'])
@login_required
def rss_list():
    return jsonify(db.get_rss_feeds())

@app.route('/api/rss', methods=['POST'])
@login_required
def rss_add():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    url  = (data.get('url') or '').strip()
    cat  = (data.get('category_hint') or 'ทั่วไป').strip()
    if not name or not url:
        return jsonify({'error': 'name และ url จำเป็น'}), 400
    try:
        fid = db.add_rss_feed(name, url, cat)
        return jsonify({'success': True, 'id': fid})
    except Exception as e:
        return jsonify({'error': f'อาจมี URL ซ้ำ: {e}'}), 400

@app.route('/api/rss/<int:fid>', methods=['PATCH'])
@login_required
def rss_update(fid):
    data = request.get_json(silent=True) or {}
    allowed = ('name','url','category_hint','enabled','auto_translate')
    kw = {k: data[k] for k in allowed if k in data}
    db.update_rss_feed(fid, **kw)
    return jsonify({'success': True})

@app.route('/api/rss/<int:fid>', methods=['DELETE'])
@login_required
def rss_delete(fid):
    db.delete_rss_feed(fid)
    return jsonify({'success': True})

@app.route('/api/rss/run', methods=['POST'])
@login_required
def rss_run_now():
    """Trigger RSS monitor in background thread."""
    def _run():
        try:
            import rss_monitor
            rss_monitor.run()
        except Exception as e:
            print(f'[RSS run] error: {e}')
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'success': True, 'message': 'RSS monitor เริ่มทำงานแล้ว (background)'})

# ════════════════════════════════════════════════════════════════════════════
#  CONFIG / SETTINGS
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    cfg = load_config()
    # Never return password
    safe = {k: v for k, v in cfg.items() if k != 'auth_password'}
    safe['auth_password_set'] = bool(cfg.get('auth_password'))
    return jsonify(safe)

@app.route('/api/config', methods=['POST'])
@login_required
def set_config():
    data = request.get_json(silent=True) or {}
    cfg  = load_config()
    allowed = ('rss_api_key','rss_api_type','rss_model','rss_max_per_feed',
               'auth_enabled','auth_password')
    for k in allowed:
        if k in data:
            cfg[k] = data[k]
    save_config(cfg)
    return jsonify({'success': True})

# ════════════════════════════════════════════════════════════════════════════
#  ENTRY
# ════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 60)
    print('  CyberSec News Intelligence')
    print('  เปิดเบราว์เซอร์ไปที่: http://localhost:5055')
    print('=' * 60)
    app.run(host='0.0.0.0', port=5055, debug=False)
