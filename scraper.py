"""
scraper.py — requests + BeautifulSoup scraper (no Selenium, no ChromeDriver needed).

Data sources tried in order:
  1. JustDial search results
  2. Sulekha search results  
  3. IndiaMart / TradeIndia listings
  4. Google search result snippets (plain HTTP)
  5. Individual business page JSON-LD schema
"""

import re
import time
import random
import logging
import json
import requests
from bs4 import BeautifulSoup
from validator import extract_phones_from_text, normalize_phone

logger = logging.getLogger(__name__)

HEADERS_LIST = [
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-IN,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
    },
    {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
]

SESSION = requests.Session()


def get_headers() -> dict:
    return random.choice(HEADERS_LIST)


def human_delay(min_s=1.0, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))


def safe_get(url: str, timeout: int = 12) -> str:
    """HTTP GET with retries. Returns page HTML or empty string."""
    for attempt in range(3):
        try:
            resp = SESSION.get(url, headers=get_headers(), timeout=timeout,
                               allow_redirects=True)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                logger.warning(f'Rate limited on {url}, waiting...')
                time.sleep(15 + attempt * 10)
            else:
                logger.debug(f'HTTP {resp.status_code} for {url}')
                return ''
        except requests.exceptions.Timeout:
            logger.debug(f'Timeout attempt {attempt+1}: {url}')
            time.sleep(3)
        except requests.exceptions.ConnectionError:
            logger.debug(f'Connection error attempt {attempt+1}: {url}')
            time.sleep(5)
        except Exception as e:
            logger.debug(f'Request error: {e}')
            return ''
    return ''


# ── JustDial Scraper ──────────────────────────────────────────────────────────
def scrape_justdial(location: str, keyword: str) -> list:
    """
    Scrape JustDial search results for business listings.
    JustDial is the most reliable source for Indian business phone numbers.
    """
    entries = []
    loc_slug = location.lower().replace(' ', '-')
    kw_slug  = keyword.lower().replace(' ', '-')
    url = f'https://www.justdial.com/{location}/{kw_slug}/nct-10215468'
    alt_url = f'https://www.justdial.com/{loc_slug}/{kw_slug}'

    for target_url in [url, alt_url]:
        html = safe_get(target_url)
        if not html:
            continue
        soup = BeautifulSoup(html, 'lxml')

        # JustDial card selectors (they change class names often, try multiple)
        cards = (
            soup.select('li.cntanr') or
            soup.select('div.resultbox_info') or
            soup.select('li[class*="store-"]') or
            soup.select('div.jdcard') or
            soup.select('script[type="application/ld+json"]')
        )

        # Try JSON-LD first (most reliable)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '{}')
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get('@graph', [data])
                else:
                    continue
                for item in items:
                    t = str(item.get('@type', ''))
                    if any(x in t for x in ['LocalBusiness','Organization','FoodEstablishment','LodgingBusiness']):
                        name = item.get('name', '').strip()
                        addr = item.get('address', {})
                        if isinstance(addr, str):
                            address = addr
                        else:
                            address = ', '.join(filter(None, [
                                addr.get('streetAddress', ''),
                                addr.get('addressLocality', ''),
                                addr.get('postalCode', ''),
                            ]))
                        tel = item.get('telephone', '') or item.get('phone', '')
                        phones = extract_phones_from_text(str(tel))
                        if not phones:
                            phones = extract_phones_from_text(soup.get_text()[:2000])
                        if name and phones:
                            entries.append({
                                'name': name,
                                'address': address or location,
                                'phone': phones[0],
                                'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
                            })
            except Exception:
                pass

        # Try card-based extraction
        for card in soup.select('li.cntanr, div[class*="resultbox"], li[class*="store"]')[:30]:
            text = card.get_text(separator=' ', strip=True)
            phones = extract_phones_from_text(text)
            if not phones:
                continue
            name_el = card.select_one(
                'span.lng_lnk_hdr, a.lng_lnk_hdr, h2, h3, '
                '[class*="title"], [class*="name"], [class*="busines"]'
            )
            name = name_el.get_text(strip=True) if name_el else ''
            addr_el = card.select_one(
                'p.addrtxt, span.addr, [class*="address"], [class*="addr"]'
            )
            address = addr_el.get_text(strip=True) if addr_el else location

            if name and len(name) > 2:
                entries.append({
                    'name': name[:100],
                    'address': address[:250],
                    'phone': phones[0],
                    'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
                })

        if entries:
            break
        human_delay(1, 2)

    return entries


# ── Sulekha Scraper ───────────────────────────────────────────────────────────
def scrape_sulekha(location: str, keyword: str) -> list:
    entries = []
    kw_slug  = keyword.lower().replace(' ', '-')
    loc_slug = location.lower().replace(' ', '-')
    url = f'https://www.sulekha.com/{kw_slug}/{loc_slug}'

    html = safe_get(url)
    if not html:
        return entries

    soup = BeautifulSoup(html, 'lxml')

    for card in soup.select('div.spcard, div[class*="biz-card"], li[class*="result"], div[class*="listing"]')[:30]:
        text = card.get_text(separator=' ', strip=True)
        phones = extract_phones_from_text(text)
        if not phones:
            continue
        name_el = card.select_one('h2, h3, [class*="name"], [class*="title"], a[class*="biz"]')
        name = name_el.get_text(strip=True) if name_el else ''
        addr_el = card.select_one('[class*="address"], [class*="addr"], p')
        address = addr_el.get_text(strip=True) if addr_el else location
        if name and len(name) > 2:
            entries.append({
                'name': name[:100],
                'address': address[:250],
                'phone': phones[0],
                'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
            })
    return entries


# ── IndiaMART / TradeIndia Scraper ────────────────────────────────────────────
def scrape_indiamart(location: str, keyword: str) -> list:
    entries = []
    query   = f'{keyword} {location}'
    url     = f'https://dir.indiamart.com/search.mp?ss={requests.utils.quote(query)}'

    html = safe_get(url)
    if not html:
        return entries

    soup = BeautifulSoup(html, 'lxml')
    for card in soup.select('div.bname, div[class*="company"], div[class*="card"]')[:20]:
        text = card.get_text(separator=' ', strip=True)
        phones = extract_phones_from_text(text)
        if not phones:
            continue
        name_el = card.select_one('a, h2, h3, span[class*="name"]')
        name = name_el.get_text(strip=True) if name_el else ''
        if name and len(name) > 2:
            entries.append({
                'name': name[:100],
                'address': location,
                'phone': phones[0],
                'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
            })
    return entries


# ── Google Snippet Scraper ────────────────────────────────────────────────────
def scrape_google_snippets(query: str, location: str) -> list:
    """
    Extract phone numbers from Google search result snippets.
    Does NOT click links — reads the snippet text directly.
    """
    entries = []
    encoded = requests.utils.quote(query)
    url = f'https://www.google.com/search?q={encoded}&num=20&hl=en'

    html = safe_get(url)
    if not html or 'captcha' in html.lower():
        logger.debug('Google snippet: blocked or captcha')
        return entries

    soup = BeautifulSoup(html, 'lxml')
    # Each result block
    for block in soup.select('div.g, div[data-hveid], div[class*="MjjYud"]')[:15]:
        text = block.get_text(separator=' ', strip=True)
        phones = extract_phones_from_text(text)
        if not phones:
            continue
        # Title as name
        title_el = block.select_one('h3')
        name = title_el.get_text(strip=True) if title_el else ''
        # Snippet as address hint
        snippet_el = block.select_one(
            'div[class*="VwiC3b"], div[class*="s3v9rd"], span[class*="aCOpRe"]'
        )
        snippet = snippet_el.get_text(strip=True) if snippet_el else ''
        pin_match = re.search(r'\d{6}', snippet)
        address = snippet[:200] if pin_match else location
        if name and len(name) > 2:
            entries.append({
                'name': name[:100],
                'address': address,
                'phone': phones[0],
                'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
            })
    return entries


# ── Page-level JSON-LD Scraper ────────────────────────────────────────────────
def scrape_page_jsonld(url: str, location: str) -> list:
    entries = []
    html = safe_get(url)
    if not html:
        return entries
    soup = BeautifulSoup(html, 'lxml')
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            items = data if isinstance(data, list) else data.get('@graph', [data])
            for item in items:
                t = str(item.get('@type', ''))
                if any(x in t for x in ['LocalBusiness','Restaurant','Hotel',
                                         'LodgingBusiness','FoodEstablishment']):
                    name = item.get('name', '').strip()
                    addr = item.get('address', {})
                    address = addr if isinstance(addr, str) else ', '.join(filter(None, [
                        addr.get('streetAddress', ''), addr.get('addressLocality', ''),
                        addr.get('addressRegion', ''), addr.get('postalCode', ''),
                    ]))
                    tel = str(item.get('telephone', '') or item.get('phone', ''))
                    phones = extract_phones_from_text(tel)
                    if name and phones:
                        entries.append({
                            'name': name,
                            'address': address or location,
                            'phone': phones[0],
                            'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
                        })
        except Exception:
            pass
    return entries


# ── Master Collection Function ────────────────────────────────────────────────
def collect_from_all_sources(location: str, keyword: str, query: str) -> list:
    """Try all data sources and aggregate results."""
    all_entries = []

    logger.debug(f'JustDial: {keyword} in {location}')
    all_entries += scrape_justdial(location, keyword)
    human_delay(0.8, 1.8)

    logger.debug(f'Sulekha: {keyword} in {location}')
    all_entries += scrape_sulekha(location, keyword)
    human_delay(0.8, 1.8)

    logger.debug(f'Google snippets: {query}')
    all_entries += scrape_google_snippets(query, location)
    human_delay(1.0, 2.0)

    return all_entries
