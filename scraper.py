import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def get_source_name(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    except Exception:
        return 'Unknown'


def clean_text(text):
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def scrape_with_trafilatura(url):
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            result = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                with_metadata=True,
                output_format='json'
            )
            if result:
                import json
                data = json.loads(result)
                title = clean_text(data.get('title', ''))
                content = clean_text(data.get('text', ''))
                if content and len(content) > 100:
                    return {
                        'title': title,
                        'content': content[:12000],
                        'source': get_source_name(url),
                        'url': url
                    }
    except Exception as e:
        print(f"[Scraper] Trafilatura error: {e}")
    return None


def scrape_with_bs4(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'lxml')

        # Remove noise
        for tag in soup(['script', 'style', 'nav', 'header', 'footer',
                         'aside', 'iframe', 'noscript', 'form', 'button']):
            tag.decompose()

        # Title
        title = ''
        for sel in ['h1', '[class*="title"]', '[class*="headline"]', 'title']:
            el = soup.find(sel)
            if el:
                candidate = clean_text(el.get_text())
                if len(candidate) > 10:
                    title = candidate
                    break

        # Content
        content = ''
        article_selectors = [
            'article',
            '[class*="article-content"]',
            '[class*="article-body"]',
            '[class*="post-content"]',
            '[class*="entry-content"]',
            '[class*="story-body"]',
            '[class*="content-body"]',
            'main',
            '[role="main"]',
        ]
        for sel in article_selectors:
            el = soup.find(sel)
            if el:
                paras = el.find_all('p')
                text = ' '.join(
                    clean_text(p.get_text())
                    for p in paras if len(p.get_text().strip()) > 40
                )
                if len(text) > 200:
                    content = text
                    break

        # Fallback
        if len(content) < 200:
            paras = soup.find_all('p')
            content = ' '.join(
                clean_text(p.get_text())
                for p in paras if len(p.get_text().strip()) > 40
            )

        if content:
            return {
                'title': title,
                'content': content[:12000],
                'source': get_source_name(url),
                'url': url
            }
    except Exception as e:
        print(f"[Scraper] BeautifulSoup error: {e}")
    return None


def scrape_article(url):
    """Try trafilatura first, then BeautifulSoup as fallback."""
    result = scrape_with_trafilatura(url)
    if result and len(result.get('content', '')) > 100:
        print(f"[Scraper] Extracted via trafilatura: {len(result['content'])} chars")
        return result

    result = scrape_with_bs4(url)
    if result and len(result.get('content', '')) > 100:
        print(f"[Scraper] Extracted via BeautifulSoup: {len(result['content'])} chars")
        return result

    print("[Scraper] Failed to extract content from URL")
    return None
