"""
validator.py — Phone number normalization, address validation, and deduplication.

Phone rules:
  - Must be a valid Indian mobile number: [6-9]XXXXXXXXX (10 digits)
  - Accepts +91, 0, or 91 prefix — normalizes to 10-digit format
  - Entries with no valid phone are skipped entirely
  - Duplicate entries identified by (name, phone) pair
"""

import re
import logging

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """Return a clean 10-digit Indian mobile number, or None if invalid."""
    if not phone or phone.strip().lower() in ('not available', 'n/a', '', 'na'):
        return None
    digits = re.sub(r'[\s\-\(\)\.]', '', str(phone))
    if digits.startswith('+91'):
        digits = digits[3:]
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
    matches = re.findall(pattern, text)
    result = []
    for m in matches:
        n = normalize_phone(m)
        if n and n not in result:
            result.append(n)
    return result


def is_valid_address(address: str) -> bool:
    if not address or len(address.strip()) < 10:
        return False
    noise = {'not available', 'n/a', 'address', 'location', 'india'}
    return address.lower().strip() not in noise


def deduplicate(entries: list) -> list:
    """Remove duplicate entries based on (name, phone) key."""
    seen = set()
    result = []
    for e in entries:
        key = (e.get('name', '').lower().strip(), e.get('phone', '').strip())
        if key not in seen and key[0] and key[1]:
            seen.add(key)
            result.append(e)
    return result


def validate_entries(entries: list) -> list:
    """Filter and clean a list of scraped entries."""
    valid = []
    for e in entries:
        phone = normalize_phone(e.get('phone', ''))
        if not phone:
            logger.debug(f"Skipped (no valid phone): {e.get('name')}")
            continue
        if not e.get('name', '').strip():
            continue
        e['phone'] = phone
        alt = normalize_phone(e.get('alternate_phone', ''))
        e['alternate_phone'] = alt if alt else 'Not Available'
        if not is_valid_address(e.get('address', '')):
            e['address'] = e.get('address', 'Address not available')
        valid.append(e)
    return valid
