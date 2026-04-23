"""
exporter.py — Export collected business data to a styled Excel workbook.

Output: <location>_business_data.xlsx  with 4 sheets:
  Restaurants | Lodges | Homestay_Resorts | Dhabas

Each sheet has:
  - Colored title row with location and entry count
  - Styled header row (Name | Address | Phone | Alternate Phone)
  - Zebra-striped data rows
  - Frozen panes at row 4
  - Auto-filter on all columns
"""

import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import logging

logger = logging.getLogger(__name__)

SHEET_CONFIG = {
    'Restaurants':      {'color': 'FF6B35', 'icon': '🍽️'},
    'Lodges':           {'color': '4A90D9', 'icon': '🏨'},
    'Homestay_Resorts': {'color': '27AE60', 'icon': '🌿'},
    'Dhabas':           {'color': 'E74C3C', 'icon': '🔥'},
}
COLUMNS = ['Name', 'Address', 'Phone', 'Alternate Phone']


def entries_to_df(entries: list, location: str, target: int = 75) -> pd.DataFrame:
    rows = []
    for e in entries[:target]:
        rows.append({
            'Name':            e.get('name', '').strip(),
            'Address':         e.get('address', location).strip(),
            'Phone':           e.get('phone', ''),
            'Alternate Phone': e.get('alternate_phone', 'Not Available'),
        })
    # Pad to exactly `target` rows
    while len(rows) < target:
        rows.append({
            'Name': 'Data not collected',
            'Address': location,
            'Phone': 'N/A',
            'Alternate Phone': 'Not Available',
        })
    return pd.DataFrame(rows[:target], columns=COLUMNS)


def style_sheet(ws, sheet_name: str, location: str):
    cfg = SHEET_CONFIG.get(sheet_name, {'color': '2C3E50', 'icon': '📋'})
    hdr_fill = PatternFill(start_color=cfg['color'], end_color=cfg['color'],
                           fill_type='solid')
    hdr_font = Font(name='Calibri', bold=True, color='FFFFFF', size=12)
    alt_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2',
                           fill_type='solid')
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    ws.insert_rows(1)
    ws.insert_rows(1)

    ws['A1'] = (
        f"{cfg['icon']} {sheet_name.replace('_', ' ')} "
        f"— {location.title()} Business Directory"
    )
    ws['A1'].font = Font(name='Calibri', bold=True, size=14, color=cfg['color'])
    ws['A1'].alignment = Alignment(horizontal='left', vertical='center')
    ws.row_dimensions[1].height = 30

    ws['A2'] = f"Total Entries: {ws.max_row - 3}  |  Location: {location.title()}"
    ws['A2'].font = Font(name='Calibri', italic=True, size=10, color='666666')
    ws.row_dimensions[2].height = 18

    for col_num, col_name in enumerate(COLUMNS, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = col_name
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[3].height = 22

    for row in ws.iter_rows(min_row=4, max_row=ws.max_row):
        is_alt = row[0].row % 2 == 0
        for cell in row:
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            cell.border = thin_border
            cell.font = Font(name='Calibri', size=10)
            if is_alt:
                cell.fill = alt_fill

    for i, width in enumerate([40, 60, 18, 20], 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.freeze_panes = 'A4'
    ws.auto_filter.ref = f'A3:{get_column_letter(len(COLUMNS))}{ws.max_row}'


def save_temp_csv(entries: list, category: str, location: str, output_dir: str = '.'):
    """Save an incremental CSV backup for a category."""
    if not entries:
        return
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(
        output_dir, f"{location.lower()}_{category.lower()}_backup.csv"
    )
    pd.DataFrame(entries).to_csv(path, index=False, encoding='utf-8-sig')
    logger.info(f'Backup CSV saved: {path}')


def export_to_excel(data: dict, location: str, output_dir: str = '.') -> str:
    """Write all categories to a single styled .xlsx file."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{location.lower().replace(' ', '_')}_business_data.xlsx"
    filepath = os.path.join(output_dir, filename)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        for sheet_name, entries in data.items():
            entries_to_df(entries, location).to_excel(
                writer, sheet_name=sheet_name, index=False
            )

    wb = load_workbook(filepath)
    for sheet_name in data:
        if sheet_name in wb.sheetnames:
            style_sheet(wb[sheet_name], sheet_name, location)
    wb.save(filepath)

    logger.info(f'Excel exported: {filepath}')
    return filepath
