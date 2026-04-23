"""
scraper.py — Selenium + BeautifulSoup scraper with human-like behavior.
Extracts business Name, Address, Phone from Google search results and linked pages.

Strategies (in order):
  1. JSON-LD schema.org structured data
  2. hCard / vCard microformats
  3. CSS selector patterns for common listing sites
  4. Regex sweep over full page text (fallback)
"""

import time
import random
import logging
import re
import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup

from validator import extract_phones_from_text, normalize_phone

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


# ── Driver ─────────────────────────────────────────────────────────────────────
def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument('--window-size=1366,768')
    opts.add_argument('--lang=en-US')
    ua = random.choice(USER_AGENTS)
    opts.add_argument(f'--user-agent={ua}')

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=opts
        )
    except Exception:
        driver = webdriver.Chrome(options=opts)

    driver.execute_cdp_cmd('Network.setUserAgentOverride', {'userAgent': ua})
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ── Utilities ──────────────────────────────────────────────────────────────────
def human_delay(min_s: float = 1.5, max_s: float = 4.0):
    time.sleep(random.uniform(min_s, max_s))


def scroll_page(driver, scrolls: int = 3):
    for _ in range(scrolls):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 0.7);")
        time.sleep(random.uniform(0.5, 1.2))


def detect_captcha(driver) -> bool:
    indicators = ['captcha', 'unusual traffic', 'robot', 'verify you are human']
    src = driver.page_source.lower()
    return any(ind in src for ind in indicators)


# ── Google Search ──────────────────────────────────────────────────────────────
def google_search(driver, query: str, location: str) -> list:
    """Perform a Google search and return organic result URLs."""
    urls = []
    try:
        driver.get('https://www.google.com')
        human_delay(1, 2.5)

        # Accept cookie consent if shown
        try:
            btn = driver.find_element(
                By.XPATH, '//button[contains(.,"Accept") or contains(.,"I agree")]'
            )
            btn.click()
            human_delay(0.5, 1)
        except Exception:
            pass

        box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'q'))
        )
        box.clear()
        for ch in query:
            box.send_keys(ch)
            time.sleep(random.uniform(0.03, 0.12))
        human_delay(0.5, 1)
        box.send_keys(Keys.RETURN)
        human_delay(2, 4)

        if detect_captcha(driver):
            logger.warning('CAPTCHA detected. Waiting 30s...')
            time.sleep(30)
            return urls

        scroll_page(driver, scrolls=2)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        skip_domains = [
            'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'linkedin.com', 'google.com',
        ]
        for div in soup.select('div.g, div[data-sokoban-container]')[:8]:
            link = div.select_one('a[href]')
            if link:
                href = link['href']
                if href.startswith('http') and not any(d in href for d in skip_domains):
                    urls.append(href)

        # Page 2
        try:
            driver.find_element(By.ID, 'pnnext').click()
            human_delay(2, 3.5)
            if not detect_captcha(driver):
                scroll_page(driver, scrolls=2)
                soup2 = BeautifulSoup(driver.page_source, 'lxml')
                for div in soup2.select('div.g')[:5]:
                    link = div.select_one('a[href]')
                    if link and link['href'].startswith('http') \
                            and 'google.com' not in link['href']:
                        urls.append(link['href'])
        except Exception:
            pass

    except Exception as e:
        logger.warning(f'Search error: {e}')

    return list(dict.fromkeys(urls))


# ── Page Parser ────────────────────────────────────────────────────────────────
def parse_page_for_businesses(html: str, location: str, category: str) -> list:
    """Extract business entries from raw HTML using 4-strategy cascade."""
    soup = BeautifulSoup(html, 'lxml')
    entries = []
    for tag in soup(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)

    # ── Strategy 1: JSON-LD schema.org ────────────────────────────────────────
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            items = data if isinstance(data, list) else data.get('@graph', [data])
            for item in items:
                t = str(item.get('@type', ''))
                if any(x in t for x in [
                    'LocalBusiness', 'Restaurant', 'Hotel',
                    'LodgingBusiness', 'FoodEstablishment'
                ]):
                    name = item.get('name', '')
                    addr = item.get('address', {})
                    address = addr if isinstance(addr, str) else ', '.join(filter(None, [
                        addr.get('streetAddress', ''),
                        addr.get('addressLocality', ''),
                        addr.get('addressRegion', ''),
                        addr.get('postalCode', ''),
                    ]))
                    phone = item.get('telephone', '') or item.get('phone', '')
                    phones = extract_phones_from_text(phone + ' ' + text[:500])
                    if name and phones:
                        entries.append({
                            'name': name.strip(),
                            'address': address.strip() or location,
                            'phone': phones[0],
                            'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
                        })
        except Exception:
            pass

    # ── Strategy 2: Microformats ───────────────────────────────────────────────
    for card in soup.select(
        '.vcard, .h-card, [itemtype*="LocalBusiness"], [itemtype*="Restaurant"]'
    ):
        name_el  = card.select_one('.fn, [itemprop="name"]')
        phone_el = card.select_one('.tel, [itemprop="telephone"]')
        addr_el  = card.select_one('.adr, [itemprop="address"]')
        if name_el and phone_el:
            phones = extract_phones_from_text(phone_el.get_text())
            if phones:
                entries.append({
                    'name': name_el.get_text(strip=True),
                    'address': addr_el.get_text(strip=True) if addr_el else location,
                    'phone': phones[0],
                    'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
                })

    # ── Strategy 3: CSS selector patterns ────────────────────────────────────
    containers = soup.select(
        '.listing, .business-card, .result-item, .biz-listing, '
        '.company-item, article, .card, [class*="listing"], [class*="business"]'
    )
    for container in containers[:30]:
        ct = container.get_text(separator=' ', strip=True)
        phones = extract_phones_from_text(ct)
        if not phones:
            continue
        name_el = container.select_one(
            'h1, h2, h3, h4, .name, .title, [class*="name"], [class*="title"]'
        )
        name = name_el.get_text(strip=True) if name_el else ''
        addr_el = container.select_one(
            '.address, [class*="address"], [class*="location"], address'
        )
        address = addr_el.get_text(strip=True) if addr_el else ''
        if not address:
            pin = re.search(r'\d{6}', ct)
            if pin:
                address = ct[max(0, pin.start() - 120):pin.end()].strip()
        if name and len(name) > 3:
            entries.append({
                'name': name[:120],
                'address': (address or location)[:250],
                'phone': phones[0],
                'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
            })

    # ── Strategy 4: Regex sweep fallback ─────────────────────────────────────
    if len(entries) < 3:
        for m in list(re.finditer(r'(?:\+91[\s\-]?)?[6-9]\d{9}', text))[:20]:
            phone = normalize_phone(m.group())
            if not phone:
                continue
            ctx = text[max(0, m.start() - 200):m.start() + 15]
            lines = [ln.strip() for ln in ctx.split('\n') if ln.strip()]
            name = ''
            for line in reversed(lines[-4:]):
                if 3 < len(line) < 80 and not re.search(r'\d{6}', line):
                    name = line
                    break
            if name:
                entries.append({
                    'name': name,
                    'address': location,
                    'phone': phone,
                    'alternate_phone': 'Not Available',
                })

    return entries


# ── URL Scraper ────────────────────────────────────────────────────────────────
def scrape_url(driver, url: str, location: str, category: str, timeout: int = 15) -> list:
    """Visit a URL and extract business entries from the page."""
    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        human_delay(1.5, 3)
        scroll_page(driver, scrolls=2)
        return parse_page_for_businesses(driver.page_source, location, category)
    except TimeoutException:
        logger.warning(f'Timeout: {url}')
        try:
            driver.execute_script('window.stop();')
            return parse_page_for_businesses(driver.page_source, location, category)
        except Exception:
            return []
    except Exception as e:
        logger.warning(f'Error scraping {url}: {e}')
        return []


# ── Google Knowledge Panel ─────────────────────────────────────────────────────
def scrape_google_knowledge_panel(
    driver, query: str, location: str, category: str
) -> list:
    """Extract data from Google Local Pack / Knowledge Panel."""
    entries = []
    try:
        driver.get('https://www.google.com')
        human_delay(1, 2)
        box = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.NAME, 'q'))
        )
        box.clear()
        for ch in query:
            box.send_keys(ch)
            time.sleep(random.uniform(0.04, 0.1))
        box.send_keys(Keys.RETURN)
        human_delay(2, 3.5)
        if detect_captcha(driver):
            time.sleep(20)
            return entries
        scroll_page(driver, scrolls=3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        selectors = 'div[class*="VkpGBb"], div[class*="rllt__details"], div[data-cid]'
        for res in soup.select(selectors)[:10]:
            txt = res.get_text(separator=' ', strip=True)
            phones = extract_phones_from_text(txt)
            name_el = res.select_one('div[class*="dbg0pd"], span[class*="OSrXXb"], .rzDMDc')
            name = name_el.get_text(strip=True) if name_el else ''
            addr_el = res.select_one('span[class*="rllt__wrapped"]')
            address = addr_el.get_text(strip=True) if addr_el else location
            if name and phones:
                entries.append({
                    'name': name,
                    'address': address,
                    'phone': phones[0],
                    'alternate_phone': phones[1] if len(phones) > 1 else 'Not Available',
                })
    except Exception as e:
        logger.warning(f'Knowledge panel error: {e}')
    return entries
