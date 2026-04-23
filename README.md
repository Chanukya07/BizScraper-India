# BizScraper-India

Automated business listing collector for Indian cities. Scrapes Name, Address, Phone for Restaurants, Lodges, Homestay/Resorts, and Dhabas — exports to a clean Excel file.

**No Chrome. No Selenium. Just Python.**

---

## Requirements

- Python 3.8+
- Internet connection

```bash
pip install -r requirements.txt
```

---

## Run

```bash
python main.py
```

You will be prompted:

```
  Enter city/location (e.g., Rajahmundry, Vizag): Rajahmundry
  You entered: 'Rajahmundry' — correct? [Y/n]: y
```

Custom output folder:

```bash
python main.py --output ./my_data
```

---

## Output

File: `rajahmundry_business_data.xlsx`

| Sheet | Category |
|-------|----------|
| Restaurants | Restaurants, biryani, dining |
| Lodges | Budget lodges, residencies |
| Homestay_Resorts | Resorts, villas, guest houses |
| Dhabas | Dhabas, food courts, highway eateries |

Each sheet: **75 entries** with `S.No | Name | Address | Phone | Alternate Phone`

---

## Features

- Location always entered manually (no hardcoding)
- Data collected from JustDial, Sulekha, Google snippets
- Phone validation: 10-digit Indian mobile numbers only (+91 format)
- Duplicate removal by (name + phone)
- Resume capability: interrupted runs continue from where they left off
- Backup CSVs saved incrementally
- Styled Excel: color headers, zebra rows, freeze panes, auto-filter

---

## Project Structure

```
BizScraper-India/
├── main.py          Entry point
├── search.py        Query generator
├── scraper.py       requests + BeautifulSoup engine
├── validator.py     Phone validation and deduplication
├── exporter.py      Excel export
└── requirements.txt
```
