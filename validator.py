"""
validator.py — Phone validation, address check, deduplication.
"""

import re
import logging

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """Return clean 10-digit Indian mobile number, or None if invalid."""
    if not phone:
        return None
    if str(phone).strip().lower() in ('not available', 'n/a', '', 'na', 'none'):
        return None
    digits = re.sub(r'[^\d]', '', str(phone))
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and re.match(r'^[6-9]\d{9}$', digits):
        return digits
    return None


def extract_phones_from_text(text: str) -> list:
    """Extract all valid Indian mobile numbers from a block of text."""
    pattern = r'(?:\+91[\s\-]?)?(?:0)?[6-9]\d{9}'
    matches = re.findall(pattern, str(text))
    result = []
    for m in matches:
        n = normalize_phone(m)
        if n and n not in result:
            result.append(n)
    return result


def is_valid_address(address: str) -> bool:
    if not address or len(address.strip()) < 5:
        return False
    noise = {'not available', 'n/a', 'address', 'location', 'india', 'na'}
    return address.lower().strip() not in noise


def deduplicate(entries: list) -> list:
    """Remove duplicates by (name, phone) pair."""
    seen = set()
    result = []
    for e in entries:
        key = (e.get('name', '').lower().strip(), e.get('phone', '').strip())
        if key[0] and key[1] and key not in seen:
            seen.add(key)
            result.append(e)
    return result


def validate_entries(entries: list) -> list:
    """Filter, clean and validate a list of scraped business entries."""
    valid = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        phone = normalize_phone(e.get('phone', ''))
        if not phone:
            continue
        name = e.get('name', '').strip()
        if not name or len(name) < 2:
            continue
        e['phone'] = phone
        alt = normalize_phone(e.get('alternate_phone', ''))
        e['alternate_phone'] = alt if alt else 'Not Available'
        address = e.get('address', '').strip()
        e['address'] = address if is_valid_address(address) else 'Address not available'
        valid.append(e)
    return valid
