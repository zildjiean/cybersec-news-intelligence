import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'cybersec_news.db')


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        # Articles table (with stars + tags migration)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                original_title TEXT,
                thai_title TEXT,
                original_content TEXT,
                thai_content TEXT,
                thai_summary TEXT,
                thai_impact TEXT,
                thai_recommendation TEXT,
                source_name TEXT,
                severity TEXT DEFAULT 'Info',
                category TEXT DEFAULT 'ทั่วไป',
                pdf_path TEXT,
                pdf_filename TEXT,
                starred INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                tlp TEXT DEFAULT 'TLP:CLEAR',
                operator TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Migrate: add columns if not present
        for col, definition in [('starred', 'INTEGER DEFAULT 0'),
                                  ('tags', "TEXT DEFAULT ''"),
                                  ('tlp', "TEXT DEFAULT 'TLP:CLEAR'"),
                                  ('operator', "TEXT DEFAULT ''")]:
            try:
                conn.execute(f'ALTER TABLE articles ADD COLUMN {col} {definition}')
            except Exception:
                pass

        # RSS feeds table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                category_hint TEXT DEFAULT 'ทั่วไป',
                enabled INTEGER DEFAULT 1,
                auto_translate INTEGER DEFAULT 1,
                last_checked TIMESTAMP,
                last_item_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Translation jobs table (for background processing)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                step TEXT DEFAULT '',
                article_id INTEGER,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    # ── Article CRUD ─────────────────────────────────────────────────────────

    def get_article_by_url(self, url):
        conn = self.get_connection()
        row = conn.execute('SELECT * FROM articles WHERE url=?', (url,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_article_by_id(self, article_id):
        conn = self.get_connection()
        row = conn.execute('SELECT * FROM articles WHERE id=?', (article_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def save_article(self, data):
        conn = self.get_connection()
        cur = conn.execute('''
            INSERT INTO articles
            (url, original_title, thai_title, original_content, thai_content,
             thai_summary, thai_impact, thai_recommendation, source_name,
             severity, category, pdf_path, pdf_filename)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            data['url'], data['original_title'], data['thai_title'],
            data['original_content'], data['thai_content'], data['thai_summary'],
            data['thai_impact'], data['thai_recommendation'], data['source_name'],
            data['severity'], data['category'], data['pdf_path'], data['pdf_filename']
        ))
        aid = cur.lastrowid
        conn.commit(); conn.close()
        return aid

    def get_all_articles(self, limit=200, offset=0):
        conn = self.get_connection()
        rows = conn.execute('''
            SELECT id, url, original_title, thai_title, source_name,
                   severity, category, pdf_path, pdf_filename,
                   starred, tags, tlp, operator, created_at
            FROM articles ORDER BY created_at DESC LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def search_articles(self, query):
        conn = self.get_connection()
        s = f'%{query}%'
        rows = conn.execute('''
            SELECT id, url, original_title, thai_title, source_name,
                   severity, category, pdf_path, pdf_filename,
                   starred, tags, tlp, operator, created_at
            FROM articles
            WHERE thai_title LIKE ? OR original_title LIKE ?
               OR source_name LIKE ? OR category LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC LIMIT 100
        ''', (s, s, s, s, s)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_starred(self, article_id, starred):
        conn = self.get_connection()
        conn.execute('UPDATE articles SET starred=? WHERE id=?', (1 if starred else 0, article_id))
        conn.commit(); conn.close()

    def update_tags(self, article_id, tags):
        conn = self.get_connection()
        conn.execute('UPDATE articles SET tags=? WHERE id=?', (tags, article_id))
        conn.commit(); conn.close()

    def update_article_meta(self, article_id, thai_title=None, severity=None, tlp=None, operator=None):
        conn = self.get_connection()
        if thai_title is not None:
            conn.execute('UPDATE articles SET thai_title=? WHERE id=?', (thai_title, article_id))
        if severity is not None:
            conn.execute('UPDATE articles SET severity=? WHERE id=?', (severity, article_id))
        if tlp is not None:
            conn.execute('UPDATE articles SET tlp=? WHERE id=?', (tlp, article_id))
        if operator is not None:
            conn.execute('UPDATE articles SET operator=? WHERE id=?', (operator, article_id))
        conn.commit(); conn.close()

    def delete_article(self, article_id):
        conn = self.get_connection()
        conn.execute('DELETE FROM articles WHERE id=?', (article_id,))
        conn.commit(); conn.close()

    def count_articles(self):
        conn = self.get_connection()
        n = conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
        conn.close()
        return n

    # ── Stats ────────────────────────────────────────────────────────────────

    def get_stats(self):
        conn = self.get_connection()

        total = conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
        starred = conn.execute('SELECT COUNT(*) FROM articles WHERE starred=1').fetchone()[0]

        # This week
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        this_week = conn.execute(
            'SELECT COUNT(*) FROM articles WHERE created_at >= ?', (week_ago,)
        ).fetchone()[0]

        # Critical + High
        critical_high = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE severity IN ('Critical','High')"
        ).fetchone()[0]

        # By severity
        sev_rows = conn.execute('''
            SELECT severity, COUNT(*) as cnt FROM articles
            GROUP BY severity ORDER BY cnt DESC
        ''').fetchall()
        by_severity = {r['severity']: r['cnt'] for r in sev_rows}

        # By category (top 8)
        cat_rows = conn.execute('''
            SELECT category, COUNT(*) as cnt FROM articles
            GROUP BY category ORDER BY cnt DESC LIMIT 8
        ''').fetchall()
        by_category = {r['category']: r['cnt'] for r in cat_rows}

        # By day – last 30 days
        day_rows = conn.execute('''
            SELECT DATE(created_at) as day, COUNT(*) as cnt
            FROM articles
            WHERE created_at >= DATE('now','-30 days')
            GROUP BY day ORDER BY day
        ''').fetchall()
        by_day = [{'date': r['day'], 'count': r['cnt']} for r in day_rows]

        # Top sources
        src_rows = conn.execute('''
            SELECT source_name, COUNT(*) as cnt FROM articles
            WHERE source_name != ''
            GROUP BY source_name ORDER BY cnt DESC LIMIT 5
        ''').fetchall()
        top_sources = [{'source': r['source_name'], 'count': r['cnt']} for r in src_rows]

        # By TLP
        tlp_rows = conn.execute('''
            SELECT COALESCE(tlp,'TLP:CLEAR') as tlp, COUNT(*) as cnt
            FROM articles GROUP BY tlp ORDER BY cnt DESC
        ''').fetchall()
        by_tlp = {r['tlp']: r['cnt'] for r in tlp_rows}

        conn.close()
        return {
            'total': total, 'starred': starred,
            'this_week': this_week, 'critical_high': critical_high,
            'by_severity': by_severity, 'by_category': by_category,
            'by_day': by_day, 'top_sources': top_sources,
            'by_tlp': by_tlp,
        }

    # ── RSS Feeds ────────────────────────────────────────────────────────────

    def get_rss_feeds(self):
        conn = self.get_connection()
        rows = conn.execute('SELECT * FROM rss_feeds ORDER BY name').fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_rss_feed(self, name, url, category_hint='ทั่วไป'):
        conn = self.get_connection()
        try:
            conn.execute(
                'INSERT INTO rss_feeds (name, url, category_hint) VALUES (?,?,?)',
                (name, url, category_hint)
            )
            conn.commit()
            fid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.close()
            return fid
        except Exception as e:
            conn.close()
            raise e

    def update_rss_feed(self, feed_id, **kwargs):
        conn = self.get_connection()
        for k, v in kwargs.items():
            if k in ('name', 'url', 'category_hint', 'enabled',
                     'auto_translate', 'last_checked', 'last_item_count'):
                conn.execute(f'UPDATE rss_feeds SET {k}=? WHERE id=?', (v, feed_id))
        conn.commit(); conn.close()

    def delete_rss_feed(self, feed_id):
        conn = self.get_connection()
        conn.execute('DELETE FROM rss_feeds WHERE id=?', (feed_id,))
        conn.commit(); conn.close()

    # ── Jobs ─────────────────────────────────────────────────────────────────

    def create_job(self, job_id, url):
        conn = self.get_connection()
        conn.execute(
            'INSERT INTO jobs (id, url, status) VALUES (?,?,?)',
            (job_id, url, 'pending')
        )
        conn.commit(); conn.close()

    def update_job(self, job_id, **kwargs):
        conn = self.get_connection()
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for k, v in kwargs.items():
            if k in ('status', 'progress', 'step', 'article_id', 'error', 'updated_at'):
                conn.execute(f'UPDATE jobs SET {k}=? WHERE id=?', (v, job_id))
        conn.commit(); conn.close()

    def get_job(self, job_id):
        conn = self.get_connection()
        row = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def cleanup_old_jobs(self, hours=24):
        conn = self.get_connection()
        conn.execute(
            "DELETE FROM jobs WHERE created_at < DATETIME('now', ? || ' hours')",
            (f'-{hours}',)
        )
        conn.commit(); conn.close()
