"""
RSS Monitor – ดึงข่าวใหม่จาก RSS feeds และแปลอัตโนมัติ
รันได้โดยตรง:  python3 rss_monitor.py
หรือผ่าน Scheduled Task
"""
import os
import sys
import json
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import Database
from scraper import scrape_article
from translator import translate_article
from pdf_generator import generate_pdf

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('rss_monitor')

CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
PDF_DIR     = os.path.join(BASE_DIR, 'pdfs')
DB_PRIMARY  = os.path.join(BASE_DIR, 'cybersec_news.db')
DB_FALLBACK = os.path.join(os.path.expanduser('~'), 'cybersec_news.db')


# ─── Config helpers ───────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _db() -> Database:
    try:
        db = Database(DB_PRIMARY)
        import sqlite3; sqlite3.connect(DB_PRIMARY).close()
        return db
    except Exception:
        return Database(DB_FALLBACK)


# ─── RSS fetching ─────────────────────────────────────────────────────────────

def fetch_feed_urls(feed_url: str, max_items: int = 10) -> list[dict]:
    """Return list of {title, url, published} from a feed."""
    try:
        import feedparser
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries[:max_items]:
            link = entry.get('link', '')
            title = entry.get('title', '')
            if link and link.startswith('http'):
                items.append({'title': title, 'url': link})
        log.info(f'Feed {feed_url}: {len(items)} items')
        return items
    except Exception as e:
        log.error(f'fetch_feed_urls error: {e}')
        return []


# ─── Per-article processing ───────────────────────────────────────────────────

def process_article(url: str, api_key: str, api_type: str, model: str,
                    db: Database) -> bool:
    """Scrape → translate → PDF → save.  Returns True on success."""
    if db.get_article_by_url(url):
        log.info(f'Skip (already translated): {url}')
        return False

    log.info(f'Scraping: {url}')
    article_data = scrape_article(url)
    if not article_data or len(article_data.get('content', '')) < 80:
        log.warning(f'Could not extract content: {url}')
        return False

    log.info(f'Translating: {article_data.get("title", "")[:60]}')
    try:
        translated = translate_article(article_data, api_key, api_type, model)
    except Exception as e:
        log.error(f'Translation error: {e}')
        return False
    if not translated:
        return False

    translated['source_name'] = article_data.get('source', '')
    translated['url']         = url

    pdf_ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_name = f'rss_{pdf_ts}.pdf'
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    os.makedirs(PDF_DIR, exist_ok=True)

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

    generate_pdf(translated, pdf_path)
    log.info(f'[✓] Saved article id={aid}: {translated["thai_title"][:50]}')
    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def run():
    cfg = load_config()
    api_key  = cfg.get('rss_api_key', '')
    api_type = cfg.get('rss_api_type', 'gemini')
    model    = cfg.get('rss_model', 'gemini-2.0-flash')
    max_per_feed = int(cfg.get('rss_max_per_feed', 5))

    if not api_key:
        log.error('rss_api_key not set in config.json – aborting')
        return

    db   = _db()
    feeds = [f for f in db.get_rss_feeds() if f['enabled'] and f['auto_translate']]
    log.info(f'Running RSS monitor: {len(feeds)} enabled feeds')

    total_new = 0
    for feed in feeds:
        log.info(f'--- Feed: {feed["name"]} ---')
        items = fetch_feed_urls(feed['url'], max_per_feed)
        new_count = 0
        for item in items:
            ok = process_article(item['url'], api_key, api_type, model, db)
            if ok:
                new_count += 1

        db.update_rss_feed(
            feed['id'],
            last_checked=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            last_item_count=new_count,
        )
        total_new += new_count

    log.info(f'RSS monitor done. New articles translated: {total_new}')


if __name__ == '__main__':
    run()
