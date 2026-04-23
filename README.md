<div align="center">

# 🏢 BizScraper-India

**End-to-end Python automation tool to collect structured business listings for any Indian city.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Selenium](https://img.shields.io/badge/Selenium-4.18-green?logo=selenium&logoColor=white)](https://selenium.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Made with ❤️](https://img.shields.io/badge/Made%20in-India%20🇮🇳-orange)]()

</div>

---

## ✨ What It Does

Enter any Indian city at runtime → the system automatically searches Google → scrapes business data → validates phone numbers → exports a clean, styled Excel file with **4 sheets × 75 entries each**.

```
User enters "Rajahmundry"
        ↓
Dynamic keyword queries generated per category
        ↓
Google searched with human-like behavior (Selenium)
        ↓
Top result pages scraped (JSON-LD → microformats → CSS → regex)
        ↓
Phone numbers validated (10-digit Indian format only)
        ↓
Duplicates removed (name + phone deduplication)
        ↓
📄 rajahmundry_business_data.xlsx  ← 4 styled sheets, 75 entries each
```

---

## 📦 Project Structure

```
BizScraper-India/
├── main.py          ← Entry point — run this
├── search.py        ← Dynamic Google query generator
├── scraper.py       ← Selenium + BeautifulSoup scraping engine
├── validator.py     ← Phone validation, address check, deduplication
├── exporter.py      ← Styled Excel export (openpyxl)
├── requirements.txt ← Python dependencies
└── .gitignore
```

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Chanukya07/BizScraper-India.git
cd BizScraper-India
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Chrome required.** `webdriver-manager` downloads ChromeDriver automatically.
> Install Chrome: [google.com/chrome](https://google.com/chrome)

### 3. Run

```bash
# Interactive — prompts you to enter a city
python main.py

# Supply city directly via CLI
python main.py --location "Rajahmundry"

# Visible browser (great for debugging / CAPTCHA solving)
python main.py --location "Vijayawada" --no-headless

# Custom output folder
python main.py --location "Hyderabad" --output ./my_data
```

---

## 📋 Output Format

**Filename:** `<location>_business_data.xlsx`

| Sheet | Category | Entries |
|-------|----------|---------|
| 🍽️ Restaurants | Restaurants, biryani, veg meals, dining | 75 |
| 🏨 Lodges | Lodges, residencies, dormitories, budget hotels | 75 |
| 🌿 Homestay_Resorts | Resorts, homestays, villas, farmstays, guest houses | 75 |
| 🔥 Dhabas | Dhabas, food plazas, food courts, highway eateries | 75 |

**Columns per sheet:**

| Name | Address | Phone | Alternate Phone |
|------|---------|-------|-----------------|
| Business name | Full address with pincode | Primary 10-digit number | Secondary number or "Not Available" |

---

## 🔍 Data Collection Strategy

### Query Generation (`search.py`)
For each category, 20 keyword variations are generated dynamically:
```python
# If location = "Rajahmundry"
"restaurant in Rajahmundry with phone number contact details"
"best biryani restaurant in Rajahmundry phone number"
"veg meals restaurant in Rajahmundry address and contact number"
# ... and 17 more
```

### 4-Strategy Extraction Cascade (`scraper.py`)
1. **JSON-LD** — `schema.org` structured data (`LocalBusiness`, `Restaurant`, `Hotel`)
2. **Microformats** — hCard / vCard (`itemtype`, `.vcard`, `.h-card`)
3. **CSS Selectors** — Common listing page patterns (`.listing`, `.business-card`, `article`)
4. **Regex sweep** — Fallback regex for phone numbers + surrounding context

### Phone Validation (`validator.py`)
```
Accepts:  +91-9876543210  |  09876543210  |  9876543210
Normalizes to:  9876543210  (10-digit, starts with 6-9)
Rejects: landlines, short codes, invalid formats
```

---

## 🛡️ Anti-Detection Features

| Feature | Implementation |
|---------|----------------|
| Human-like typing | 30–120ms random delay per keystroke |
| Request pacing | 1.5–4s random delay between pages |
| User-Agent rotation | 3 real Chrome UA strings |
| WebDriver masking | `navigator.webdriver = undefined` via CDP |
| Scroll simulation | Mimics reading behavior |
| CAPTCHA detection | Auto-pauses 30s, logs warning |
| Retry logic | 3 attempts with exponential backoff |

---

## 🔄 Resume Capability

If interrupted (`Ctrl+C` or crash), progress is saved to `resume_state.json`.
Re-run with the **same location** — completed categories are skipped automatically.
`resume_state.json` is deleted on successful completion.

---

## 📝 Logs

| Destination | Level | Content |
|------------|-------|---------|
| Console (stdout) | INFO | Search queries, progress, results |
| `scraper.log` | DEBUG | Full trace including skipped entries |

---

## 🗂️ Backup CSVs

Saved incrementally during collection:
```
output/rajahmundry_restaurants_backup.csv
output/rajahmundry_lodges_backup.csv
output/rajahmundry_homestay_resorts_backup.csv
output/rajahmundry_dhabas_backup.csv
```

---

## ⚙️ Configuration

**Add more keywords** → edit `CATEGORY_KEYWORDS` in `search.py`

**Change target entries** → edit `TARGET = 75` in `main.py`

**Adjust delays** → edit `human_delay()` calls in `scraper.py`

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|-----------|
| `ChromeDriver not found` | Install Chrome or run `pip install webdriver-manager` |
| CAPTCHA blocking | Use `--no-headless` to solve manually, or add a VPN |
| Fewer than 75 entries | Area has limited online presence — results are padded with placeholder rows |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Slow collection | Normal — delays are intentional to avoid IP blocks |

---

## ⚠️ Disclaimer

This tool is for educational and research purposes. Always respect website Terms of Service. Use responsibly with appropriate rate limiting.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">
Built with 🐍 Python · 🌐 Selenium · 🍜 BeautifulSoup · 📊 Pandas
</div>
