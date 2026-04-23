"""
search.py — Dynamic search query generator.
All queries built at runtime from user-supplied location. Nothing hardcoded.
"""

CATEGORY_KEYWORDS = {
    'Restaurants': [
        'restaurant', 'biryani restaurant', 'veg meals',
        'family restaurant', 'south indian restaurant',
        'north indian restaurant', 'pure veg restaurant',
        'hotel dining', 'food restaurant', 'tiffin center',
    ],
    'Lodges': [
        'lodge', 'budget lodge', 'residency hotel',
        'dormitory', 'ac lodge', 'non ac lodge',
        'guest lodge', 'stay hotel', 'inn', 'budget hotel',
    ],
    'Homestay_Resorts': [
        'resort', 'homestay', 'villa',
        'farmstay', 'guest house', 'service apartment',
        'holiday resort', 'eco resort', 'luxury resort', 'cottages',
    ],
    'Dhabas': [
        'dhaba', 'food plaza', 'food court',
        'highway dhaba', 'punjabi dhaba', 'barbeque',
        'non veg dhaba', 'roadside dhaba', 'diner', 'fast food',
    ],
}

QUERY_TEMPLATES = [
    '{kw} in {loc} phone number contact',
    '{kw} in {loc} address phone',
    'best {kw} in {loc} contact details',
    '{loc} {kw} phone number',
    '{kw} near {loc} contact',
]


def generate_queries(location: str, category: str, max_queries: int = 25) -> list:
    keywords = CATEGORY_KEYWORDS.get(category, [])
    queries = []
    for i, kw in enumerate(keywords):
        tmpl = QUERY_TEMPLATES[i % len(QUERY_TEMPLATES)]
        queries.append(tmpl.format(kw=kw, loc=location))
        queries.append(f'{kw} in {location} with phone number')
    queries.append(f'top {category.lower().replace("_", " ")} in {location} contact')
    queries.append(f'{location} {category.lower().replace("_", " ")} list address phone')
    return list(dict.fromkeys(queries))[:max_queries]


def get_all_queries(location: str) -> dict:
    return {cat: generate_queries(location, cat) for cat in CATEGORY_KEYWORDS}
