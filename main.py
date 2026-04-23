"""
main.py — BizScraper-India entry point.

Usage:
    python main.py
    python main.py --output ./my_data

Location is ALWAYS entered manually by the user. No CLI arg, no hardcoding.
"""

import argparse
import logging
import os
import sys
import json
import time

from search import get_all_queries, CATEGORY_KEYWORDS
from scraper import collect_from_all_sources, human_delay
from validator import validate_entries, deduplicate
from exporter import export_to_excel, save_temp_csv

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scraper.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

CATEGORIES     = list(CATEGORY_KEYWORDS.keys())
TARGET         = 75
COLLECT_TARGET = 100
RESUME_FILE    = 'resume_state.json'


# ── Resume ────────────────────────────────────────────────────────────────────
def load_resume(location: str) -> dict:
    if os.path.exists(RESUME_FILE):
        try:
            with open(RESUME_FILE, encoding='utf-8') as f:
                state = json.load(f)
            if state.get('location', '').lower() == location.lower():
                logger.info('Resuming previous session...')
                return state
        except Exception:
            pass
    return {'location': location, 'data': {c: [] for c in CATEGORIES}}


def save_resume(location: str, data: dict):
    try:
        with open(RESUME_FILE, 'w', encoding='utf-8') as f:
            json.dump({'location': location, 'data': data}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f'Could not save resume state: {e}')


# ── Progress Bar ──────────────────────────────────────────────────────────────
def print_progress(category: str, n: int):
    filled = int(30 * min(n, TARGET) / TARGET)
    bar = '#' * filled + '-' * (30 - filled)
    pct = min(100, n * 100 // TARGET)
    sys.stdout.write(f'\r  [{bar}] {n:>3}/{TARGET} {category:<20} ({pct}%)')
    sys.stdout.flush()


# ── Core Collector ────────────────────────────────────────────────────────────
def collect_category(category: str, queries: list, location: str,
                     existing: list, output_dir: str) -> list:
    entries = list(existing)
    keywords = CATEGORY_KEYWORDS.get(category, [])

    print(f'\n')
    print(f'  =================================================')
    print(f'  Collecting : {category.replace("_", " ")}')
    print(f'  Location   : {location.title()}')
    print(f'  Target     : {TARGET} entries')
    print(f'  =================================================')

    query_idx = 0
    kw_idx    = 0

    while len(entries) < COLLECT_TARGET and query_idx < len(queries):
        query   = queries[query_idx]
        keyword = keywords[kw_idx % len(keywords)]
        query_idx += 1
        kw_idx    += 1

        logger.info(f'Searching: {query}')

        new_entries = collect_from_all_sources(location, keyword, query)
        entries = deduplicate(validate_entries(entries + new_entries))

        print_progress(category, len(entries))
        save_temp_csv(entries, category, location, output_dir)
        save_resume(location, {category: entries})

        if len(entries) >= COLLECT_TARGET:
            break

        human_delay(1.0, 2.5)

    print()  # newline after progress bar
    final = entries[:TARGET]
    logger.info(f'Done: {category} — {len(final)} entries')
    return final


# ── Location Input ────────────────────────────────────────────────────────────
def get_location() -> str:
    """
    Always prompts user to manually type the city name.
    Includes a confirmation step to avoid typos.
    """
    print()
    print('  +-----------------------------------------------+')
    print('  |        LOCATION INPUT — REQUIRED              |')
    print('  +-----------------------------------------------+')
    while True:
        loc = input('  Enter city/location (e.g., Rajahmundry, Vizag): ').strip()
        if not loc:
            print('  [!] Location cannot be empty. Please try again.')
            continue
        confirm = input(f"  You entered: '{loc.title()}' — correct? [Y/n]: ").strip().lower()
        if confirm in ('', 'y', 'yes'):
            return loc
        print('  Okay, let\'s try again.\n')


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description='BizScraper-India')
    ap.add_argument('--output', type=str, default='./output',
                    help='Folder to save Excel and CSV files (default: ./output)')
    args = ap.parse_args()

    print()
    print('  =================================================')
    print('  BizScraper-India')
    print('  Business Listing Data Collection System')
    print('  =================================================')

    location = get_location()
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    print(f'\n  Location   : {location.title()}')
    print(f'  Output Dir : {output_dir}')
    print(f'  Categories : {" | ".join(CATEGORIES)}')
    print()

    state     = load_resume(location)
    collected = state.get('data', {c: [] for c in CATEGORIES})
    all_queries = get_all_queries(location)

    final = {}
    for cat in CATEGORIES:
        existing = collected.get(cat, [])
        if len(existing) >= TARGET:
            print(f'\n  [SKIP] {cat} already has {len(existing)} entries.')
            final[cat] = existing[:TARGET]
            continue
        result = collect_category(cat, all_queries[cat], location, existing, output_dir)
        final[cat] = result
        collected[cat] = result
        save_resume(location, collected)

    print('\n\n  Exporting to Excel...')
    try:
        path = export_to_excel(final, location, output_dir)
        print()
        print('  =================================================')
        print('  DONE!')
        print(f'  File saved : {path}')
        print(f'  Location   : {location.title()}')
        print()
        for cat, ents in final.items():
            real = sum(1 for e in ents if e.get('phone', '') not in ('N/A', '', None))
            label = cat.replace('_', ' ')
            print(f'    {label:<22} {real:>3} / {TARGET} entries')
        print('  =================================================')
        print()
        if os.path.exists(RESUME_FILE):
            os.remove(RESUME_FILE)
    except Exception as e:
        logger.error(f'Export failed: {e}', exc_info=True)
        print(f'  [ERROR] Export failed: {e}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n  [!] Interrupted by user. Partial data saved in resume_state.json')
        print('      Run again with the same location to resume.')
        sys.exit(0)
