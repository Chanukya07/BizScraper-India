"""
main.py — Entry point for the Business Listing Data Collection System.

Usage:
    python main.py
    python main.py --no-headless
    python main.py --output ./data

NOTE: Location is ALWAYS entered manually by the user at runtime.
      It is never hardcoded or passed via CLI.
"""

import argparse
import logging
import os
import sys
import time
import json

from search import get_all_queries
from scraper import build_driver, google_search, scrape_url, scrape_google_knowledge_panel
from validator import validate_entries, deduplicate
from exporter import export_to_excel, save_temp_csv

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scraper.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

CATEGORIES     = ['Restaurants', 'Lodges', 'Homestay_Resorts', 'Dhabas']
TARGET         = 75
COLLECT_TARGET = 100
RESUME_FILE    = 'resume_state.json'


# ── Resume state ───────────────────────────────────────────────────────────────
def load_resume(location: str) -> dict:
    if os.path.exists(RESUME_FILE):
        with open(RESUME_FILE) as f:
            state = json.load(f)
        if state.get('location', '').lower() == location.lower():
            logger.info("📂 Resuming previous session...")
            return state
    return {'location': location, 'data': {c: [] for c in CATEGORIES}}


def save_resume(location: str, data: dict):
    with open(RESUME_FILE, 'w') as f:
        json.dump({'location': location, 'data': data}, f, indent=2)


# ── Progress bar ───────────────────────────────────────────────────────────────
def print_progress(category: str, n: int):
    filled = int(30 * min(n, TARGET) / TARGET)
    bar = '█' * filled + '░' * (30 - filled)
    pct = min(100, n * 100 // TARGET)
    sys.stdout.write(f"\r  [{bar}] {n}/{TARGET} {category} ({pct}%)")
    sys.stdout.flush()


# ── Core collection loop ───────────────────────────────────────────────────────
def collect_category(driver, category: str, queries: list, location: str,
                     existing: list, output_dir: str) -> list:
    entries = list(existing)
    seen_urls, q_idx = set(), 0

    print(f"\n\n{'='*55}")
    print(f"  📌 Collecting: {category.replace('_', ' ')} — Target: {TARGET}")
    print(f"{'='*55}")

    while len(entries) < COLLECT_TARGET and q_idx < len(queries):
        query = queries[q_idx]
        q_idx += 1
        logger.info(f"🔍 Query: {query}")

        # Knowledge panel (often contains phone numbers directly)
        kp = scrape_google_knowledge_panel(driver, query, location, category)
        entries = deduplicate(validate_entries(entries + kp))

        # Organic search
        for attempt in range(3):
            try:
                urls = google_search(driver, query, location)
                break
            except Exception as e:
                logger.warning(f"Search attempt {attempt+1} failed: {e}")
                time.sleep(10 * (attempt + 1))
                urls = []

        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            results = scrape_url(driver, url, location, category)
            entries = deduplicate(validate_entries(entries + results))
            print_progress(category, len(entries))
            if len(entries) >= COLLECT_TARGET:
                break

        save_temp_csv(entries, category, location, output_dir)
        save_resume(location, {category: entries})

    print()
    final = entries[:TARGET]
    logger.info(f"✅ {category}: {len(final)} entries collected (target {TARGET})")
    return final


# ── Manual location input (ALWAYS prompted, never auto-filled) ─────────────────
def get_location() -> str:
    """
    Always prompts the user to manually type the location.
    No CLI argument, no default, no hardcoding — pure interactive input.
    Keeps asking until a non-empty value is entered.
    """
    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │         📍 LOCATION INPUT REQUIRED          │")
    print("  └─────────────────────────────────────────────┘")
    while True:
        loc = input("  Enter location (e.g., Rajahmundry, Hyderabad, Vizag): ").strip()
        if loc:
            # Confirm back to user
            confirm = input(f"  ✅ You entered: '{loc.title()}' — Confirm? [Y/n]: ").strip().lower()
            if confirm in ('', 'y', 'yes'):
                return loc
            else:
                print("  🔄 Let's try again...\n")
        else:
            print("  ⚠️  Location cannot be empty. Please type a city name.")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description='BizScraper-India: Business Listing Collector')
    # NOTE: No --location argument — location is always entered manually
    ap.add_argument('--headless', action='store_true', default=True)
    ap.add_argument('--no-headless', dest='headless', action='store_false',
                    help='Show browser window (useful for debugging/CAPTCHA)')
    ap.add_argument('--output', type=str, default='./output', help='Output directory')
    args = ap.parse_args()

    print("\n" + "="*55)
    print("  🏢 BizScraper-India")
    print("  Business Listing Data Collection System")
    print("  Built with Selenium + BeautifulSoup + Pandas")
    print("="*55)

    # ── Location: ALWAYS manual user input ────────────────────────────────────
    location = get_location()
    print(f"\n  🌍 Collecting data for: {location.title()}")
    print(f"  📁 Output folder     : {args.output}")
    print(f"  🖥️  Browser mode      : {'Headless' if args.headless else 'Visible'}")
    print()

    os.makedirs(args.output, exist_ok=True)
    state    = load_resume(location)
    collected = state.get('data', {c: [] for c in CATEGORIES})
    all_queries = get_all_queries(location)

    print(f"  🚀 Starting browser...")
    driver = build_driver(headless=args.headless)

    try:
        final = {}
        for cat in CATEGORIES:
            existing = collected.get(cat, [])
            if len(existing) >= TARGET:
                print(f"\n  ✅ {cat} already complete ({len(existing)} entries). Skipping.")
                final[cat] = existing[:TARGET]
                continue
            result = collect_category(driver, cat, all_queries[cat],
                                      location, existing, args.output)
            final[cat] = result
            collected[cat] = result
            save_resume(location, collected)

        print("\n\n  📊 Exporting to Excel...")
        path = export_to_excel(final, location, args.output)

        print(f"\n{'='*55}")
        print(f"  ✅ ALL DONE!")
        print(f"  📁 Saved to: {path}")
        print(f"  📍 Location: {location.title()}")
        for cat, ents in final.items():
            real = sum(1 for e in ents if e.get('phone', '') != 'N/A')
            print(f"     • {cat.replace('_',' '):<20} {real:>3}/75 valid entries")
        print(f"{'='*55}\n")

        if os.path.exists(RESUME_FILE):
            os.remove(RESUME_FILE)

    except KeyboardInterrupt:
        print("\n\n  ⚠️  Interrupted. Progress saved. Run again to resume.")
        save_resume(location, collected)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        save_resume(location, collected)
    finally:
        driver.quit()
        logger.info("Browser closed.")


if __name__ == '__main__':
    main()
