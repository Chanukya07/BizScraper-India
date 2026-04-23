"""
search.py — Dynamic query generator for each business category.
All queries are composed at runtime using the user-supplied location.
"""

CATEGORY_KEYWORDS = {
    'Restaurants': [
        'restaurant',
        'biryani restaurant',
        'veg meals restaurant',
        'family restaurant',
        'hotel restaurant',
        'dining restaurant',
        'food restaurant',
        'pure veg restaurant',
        'south indian restaurant',
        'north indian restaurant',
    ],
    'Lodges': [
        'lodge',
        'residency lodge',
        'dormitory',
        'budget lodge',
        'budget hotel',
        'hotel lodge',
        'stay lodge',
        'ac lodge',
        'non ac lodge',
        'guest lodge',
    ],
    'Homestay_Resorts': [
        'resort',
        'homestay',
        'villa resort',
        'farmstay',
        'guest house',
        'service apartment',
        'holiday resort',
        'eco resort',
        'beach resort',
        'luxury resort',
    ],
    'Dhabas': [
        'dhaba',
        'food plaza',
        'food court',
        'barbeque dhaba',
        'highway dhaba',
        'punjabi dhaba',
        'pure veg dhaba',
        'non veg dhaba',
        'roadside dhaba',
        'diner',
    ],
}

QUERY_SUFFIXES = [
    'with phone number contact details',
    'address and contact number',
    'contact address phone',
    'phone number address',
    'details contact information',
]


def generate_queries(location: str, category: str, max_queries: int = 20) -> list:
    """Generate a list of search queries for a category + location."""
    keywords = CATEGORY_KEYWORDS.get(category, [])
    queries = []
    for i, kw in enumerate(keywords):
        suffix = QUERY_SUFFIXES[i % len(QUERY_SUFFIXES)]
        queries.append(f"{kw} in {location} {suffix}")
        queries.append(f"best {kw} in {location} phone number")
    queries.append(f"top {category.lower().replace('_', ' ')} in {location} with contact")
    queries.append(f"{location} {category.lower().replace('_', ' ')} list phone address")
    return queries[:max_queries]


def get_all_queries(location: str) -> dict:
    """Return query lists for all 4 categories."""
    return {cat: generate_queries(location, cat) for cat in CATEGORY_KEYWORDS}
