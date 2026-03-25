"""
CyberSec News Intelligence – Flask Application
แปลข่าว Cybersecurity เป็นภาษาไทย และสร้างรายงาน PDF สำหรับผู้บริหาร / CISO
"""
__version__      = "1.1.0"
__release_date__ = "2026-03-25"

import os, re, json, uuid, threading, io, base64
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, jsonify,
                   send_file, session, redirect, url_for)

import bcrypt as _bcrypt
import pyotp
import qrcode

from database import Database
from scraper import scrape_article
from translator import translate_article
from pdf_generator import generate_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR  = os.path.join(BASE_DIR, 'pdfs')
os.makedirs(PDF_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 hours

# ── DB (with fallback) ──────────────────────────────────────────────────────
_DB_PRIMARY  = os.path.join(BASE_DIR, 'cybersec_news.db')
_DB_FALLBACK = os.path.join(os.path.expanduser('~'), 'cybersec_news.db')
try:
    db = Database(_DB_PRIMARY)
    import sqlite3 as _sq; _sq.connect(_DB_PRIMARY).close()
except Exception:
    db = Database(_DB_FALLBACK)

# ── Default admin on first run ───────────────────────────────────────────────
def _init_default_admin():
    if db.get_user_count() == 0:
        _default_pw  = 'Admin@1234'
        _pw_hash     = _bcrypt.hashpw(_default_pw.encode(), _bcrypt.gensalt()).decode()
        _totp_secret = pyotp.random_base32()
        db.create_user('admin', _pw_hash, _totp_secret, role='admin')
        print('=' * 60)
        print('  [!] Default admin created')
        print(f'  Username : admin')
        print(f'  Password : {_default_pw}')
        print('  Please change password after first login')
        print('=' * 60)

_init_default_admin()

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

# ── Auth decorators ─────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authed'):
            if request.is_json:
                return jsonify(error='Unauthorized'), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            if request.is_json:
                return jsonify(error='Forbidden — Admin only'), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ── Helpers ─────────────────────────────────────────────────────────────────
def safe_filename(title: str, aid: int) -> str:
    safe = re.sub(r'[^\w\u0E00-\u0E7F\-]', '_', title)[:40]
    ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'cybersec_{aid}_{ts}.pdf'

def _make_qr_b64(uri: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=6, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

# ════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if session.get('authed'):
        return redirect(url_for('index'))
    err = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '')
        user = db.get_user_by_username(username)
        if user and user.get('is_active') and \
                _bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            # Password OK → proceed to TOTP step
            session['_pending_uid']  = user['id']
            session['_pending_name'] = user['username']
            session['_pending_role'] = user['role']
            if not user.get('totp_verified'):
                return redirect(url_for('setup_totp'))
            return redirect(url_for('login_totp'))
        err = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง หรือบัญชีถูกระงับ'
    return render_template('login.html', error=err)

@app.route('/login/totp', methods=['GET', 'POST'])
def login_totp():
    uid = session.get('_pending_uid')
    if not uid:
        return redirect(url_for('login_page'))
    err = None
    if request.method == 'POST':
        token = (request.form.get('totp_code') or '').strip().replace(' ', '')
        user  = db.get_user(uid)
        if user and pyotp.TOTP(user['totp_secret']).verify(token, valid_window=1):
            _finalize_login(user)
            return redirect(url_for('index'))
        err = 'รหัส OTP ไม่ถูกต้อง กรุณาตรวจสอบเวลาบนอุปกรณ์และลองใหม่'
    return render_template('login_totp.html',
                           username=session.get('_pending_name'), error=err)

@app.route('/login/setup-totp', methods=['GET', 'POST'])
def setup_totp():
    uid = session.get('_pending_uid')
    if not uid:
        return redirect(url_for('login_page'))
    user = db.get_user(uid)
    if not user:
        return redirect(url_for('login_page'))

    totp = pyotp.TOTP(user['totp_secret'])
    uri  = totp.provisioning_uri(
        name=user['username'], issuer_name='CyberSec Intelligence')
    qr_b64 = _make_qr_b64(uri)

    err = None
    if request.method == 'POST':
        token = (request.form.get('totp_code') or '').strip().replace(' ', '')
        if totp.verify(token, valid_window=1):
            db.mark_totp_verified(uid)
            user['totp_verified'] = 1
            _finalize_login(user)
            return redirect(url_for('index'))
        err = 'รหัส OTP ไม่ถูกต้อง กรุณาลองสแกน QR code ใหม่'
    return render_template('setup_totp.html',
                           qr_b64=qr_b64,
                           totp_secret=user['totp_secret'],
                           username=user['username'],
                           error=err)

def _finalize_login(user: dict):
    pending_uid  = session.pop('_pending_uid',  None)
    pending_name = session.pop('_pending_name', None)
    pending_role = session.pop('_pending_role', None)
    session.clear()
    session.permanent = True
    session['authed']   = True
    session['user_id']  = user['id']
    session['username'] = user['username']
    session['role']     = user['role']
    db.update_last_login(user['id'])

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
    cfg = db.get_system_config()
    has_server_key = bool(cfg.get('api_key'))
    return render_template('index.html',
                           app_version=__version__,
                           release_date=__release_date__,
                           current_user=session.get('username'),
                           current_role=session.get('role', 'user'),
                           has_server_key=has_server_key)

@app.route('/api/version')
def api_version():
    return jsonify(version=__version__, release_date=__release_date__)

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

    if not url:
        return jsonify({'error': 'กรุณาระบุ URL'}), 400

    # ── ถ้าไม่มี api_key จาก client ให้ใช้ server-side key ──
    if not api_key:
        api_key  = db.get_config_value('api_key')
        api_type = db.get_config_value('api_type') or api_type
        model    = db.get_config_value('api_model') or model

    if not api_key:
        return jsonify({'error': 'กรุณาระบุ API Key หรือให้ Admin ตั้งค่า Server API Key'}), 400

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
    def _run():
        try:
            import rss_monitor
            rss_monitor.run()
        except Exception as e:
            print(f'[RSS run] error: {e}')
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'success': True, 'message': 'RSS monitor เริ่มทำงานแล้ว (background)'})

# ════════════════════════════════════════════════════════════════════════════
#  SYSTEM CONFIG  (Admin only)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/system-config', methods=['GET'])
@login_required
@admin_required
def get_system_config():
    cfg = db.get_system_config()
    # Mask secrets before sending to frontend
    safe = dict(cfg)
    if safe.get('api_key'):
        safe['api_key'] = safe['api_key'][:6] + '••••••••'
    if safe.get('smtp_password'):
        safe['smtp_password'] = '••••••••'
    safe['api_key_set']      = bool(cfg.get('api_key'))
    safe['smtp_password_set'] = bool(cfg.get('smtp_password'))
    return jsonify(safe)

@app.route('/api/system-config', methods=['POST'])
@login_required
@admin_required
def set_system_config():
    data = request.get_json(silent=True) or {}
    # Strip placeholder masks — don't overwrite real values with masks
    if data.get('api_key', '').endswith('••••••••'):
        data.pop('api_key', None)
    if data.get('smtp_password') == '••••••••':
        data.pop('smtp_password', None)
    db.update_system_config(data)
    return jsonify({'success': True})

# ════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT  (Admin only)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def users_list():
    return jsonify(db.get_all_users())

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def users_create():
    data     = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    role     = data.get('role', 'user')

    if not username or not password:
        return jsonify({'error': 'username และ password จำเป็น'}), 400
    if role not in ('admin', 'user'):
        return jsonify({'error': 'role ต้องเป็น admin หรือ user'}), 400
    if len(password) < 8:
        return jsonify({'error': 'password ต้องมีอย่างน้อย 8 ตัวอักษร'}), 400

    if db.get_user_by_username(username):
        return jsonify({'error': f'username "{username}" ถูกใช้แล้ว'}), 409

    pw_hash     = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    totp_secret = pyotp.random_base32()
    uid = db.create_user(username, pw_hash, totp_secret, role)
    return jsonify({'success': True, 'id': uid,
                    'message': f'สร้างผู้ใช้ "{username}" เรียบร้อย — '
                               'ผู้ใช้ต้องตั้งค่า Google Authenticator เมื่อ login ครั้งแรก'})

@app.route('/api/users/<int:uid>', methods=['PATCH'])
@login_required
@admin_required
def users_update(uid):
    data = request.get_json(silent=True) or {}
    # Prevent admin from demoting/deactivating themselves
    if uid == session.get('user_id') and \
            ('role' in data or 'is_active' in data):
        return jsonify({'error': 'ไม่สามารถแก้ไข role หรือ status ของตัวเองได้'}), 400

    if 'is_active' in data:
        db.update_user(uid, is_active=1 if data['is_active'] else 0)
    if 'role' in data and data['role'] in ('admin', 'user'):
        db.update_user(uid, role=data['role'])
    if 'password' in data:
        if len(data['password']) < 8:
            return jsonify({'error': 'password ต้องมีอย่างน้อย 8 ตัวอักษร'}), 400
        pw_hash = _bcrypt.hashpw(data['password'].encode(), _bcrypt.gensalt()).decode()
        db.update_user(uid, password_hash=pw_hash)
    if data.get('reset_totp'):
        new_secret = pyotp.random_base32()
        db.update_user(uid, totp_secret=new_secret, totp_verified=0)
    return jsonify({'success': True})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@login_required
@admin_required
def users_delete(uid):
    if uid == session.get('user_id'):
        return jsonify({'error': 'ไม่สามารถลบบัญชีของตัวเองได้'}), 400
    db.delete_user(uid)
    return jsonify({'success': True})

# ── Change own password ──────────────────────────────────────────────────────
@app.route('/api/me/password', methods=['POST'])
@login_required
def change_own_password():
    data     = request.get_json(silent=True) or {}
    old_pw   = (data.get('old_password') or '')
    new_pw   = (data.get('new_password') or '')
    user     = db.get_user(session['user_id'])
    stored_hash = user['password_hash']
    # handle both str and bytes from DB
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode()
    if not _bcrypt.checkpw(old_pw.encode(), stored_hash):
        return jsonify({'ok': False, 'error': 'รหัสผ่านเดิมไม่ถูกต้อง'}), 400
    if len(new_pw) < 8:
        return jsonify({'ok': False, 'error': 'รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร'}), 400
    pw_hash = _bcrypt.hashpw(new_pw.encode(), _bcrypt.gensalt()).decode()
    db.update_user(session['user_id'], password_hash=pw_hash)
    return jsonify({'ok': True})

# ════════════════════════════════════════════════════════════════════════════
#  ENTRY
# ════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 60)
    print('  CyberSec News Intelligence')
    print('  เปิดเบราว์เซอร์ไปที่: http://localhost:5055')
    print('=' * 60)
    app.run(host='0.0.0.0', port=5055, debug=False)
