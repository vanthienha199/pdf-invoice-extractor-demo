"""Write the extracted invoices to Excel and CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .parse import Invoice

# The spreadsheet is the thing a client opens first, so it is styled rather than
# dumped. Calibri is the font Excel already has on Windows and on a Mac, which
# keeps the file looking the same on the client's machine as it does here.
BODY_FONT = Font(name="Arial", size=11, color="2A2924")
REVIEW_FONT = Font(name="Arial", size=11, color="8A4B0B")
HEADER_FILL = PatternFill("solid", fgColor="1E2126")
HEADER_FONT = Font(name="Arial", size=11, color="F3EFE7", bold=True)
REVIEW_FILL = PatternFill("solid", fgColor="FBE7D2")
BAND_FILL = PatternFill("solid", fgColor="FAF8F4")
THIN = Side(style="thin", color="E4DED3")
BORDER = Border(bottom=THIN)
MONEY_FMT = '"$"#,##0.00'
RIGHT = Alignment(horizontal="right")
LEFT = Alignment(horizontal="left", vertical="center")

INVOICE_COLUMNS = [
    ("source_file", 38), ("vendor", 24), ("invoice_number", 16), ("invoice_date", 13),
    ("currency", 9), ("net", 12), ("tax", 11), ("total", 12), ("line_items", 11),
    ("pages", 7), ("confidence", 11), ("needs_review", 14), ("flags", 60),
]
ITEM_COLUMNS = [
    ("source_file", 38), ("invoice_number", 16), ("vendor", 24), ("description", 52),
    ("quantity", 10), ("unit_price", 12), ("amount", 12),
]


NUMERIC = {"net", "tax", "total", "unit_price", "amount", "quantity", "line_items", "pages", "confidence"}


def _style_header(sheet, columns) -> None:
    for index, (name, width) in enumerate(columns, start=1):
        cell = sheet.cell(row=1, column=index, value=name.replace("_", " ").title())
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = RIGHT if name in NUMERIC else LEFT
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.row_dimensions[1].height = 24
    sheet.freeze_panes = "A2"


def to_excel(invoices: list[Invoice], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook()

    sheet = book.active
    sheet.title = "Invoices"
    _style_header(sheet, INVOICE_COLUMNS)
    # Anything needing a human sits at the top, because that is the only part of
    # the sheet a client has to act on.
    ordered = sorted(invoices, key=lambda i: (not i.needs_review, i.vendor, i.invoice_date))
    for row_index, invoice in enumerate(ordered, start=2):
        row = invoice.as_row()
        for col_index, (name, _) in enumerate(INVOICE_COLUMNS, start=1):
            cell = sheet.cell(row=row_index, column=col_index, value=row[name])
            cell.font = REVIEW_FONT if invoice.needs_review else BODY_FONT
            cell.border = BORDER
            if name in ("net", "tax", "total"):
                cell.number_format = MONEY_FMT
            elif name == "confidence":
                cell.number_format = "0.00"
            elif name in NUMERIC:
                cell.number_format = "0"
            if invoice.needs_review:
                cell.fill = REVIEW_FILL
            elif row_index % 2 == 0:
                cell.fill = BAND_FILL
        sheet.row_dimensions[row_index].height = 18
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(INVOICE_COLUMNS))}{len(invoices) + 1}"

    items = book.create_sheet("Line items")
    _style_header(items, ITEM_COLUMNS)
    row_index = 2
    for invoice in invoices:
        for item in invoice.line_items:
            values = {
                "source_file": invoice.source_file,
                "invoice_number": invoice.invoice_number,
                "vendor": invoice.vendor,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.amount,
            }
            for col_index, (name, _) in enumerate(ITEM_COLUMNS, start=1):
                cell = items.cell(row=row_index, column=col_index, value=values[name])
                cell.font = BODY_FONT
                cell.border = BORDER
                if name in ("unit_price", "amount"):
                    cell.number_format = MONEY_FMT
                elif name == "quantity":
                    cell.number_format = "0"
                if row_index % 2 == 0:
                    cell.fill = BAND_FILL
            items.row_dimensions[row_index].height = 18
            row_index += 1

    book.save(path)
    return path


def to_csv(invoices: list[Invoice], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[name for name, _ in INVOICE_COLUMNS])
        writer.writeheader()
        for invoice in invoices:
            writer.writerow(invoice.as_row())
    return path


def items_to_csv(invoices: list[Invoice], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([name for name, _ in ITEM_COLUMNS])
        for invoice in invoices:
            for item in invoice.line_items:
                writer.writerow([
                    invoice.source_file, invoice.invoice_number, invoice.vendor,
                    item.description, item.quantity, f"{item.unit_price:.2f}", f"{item.amount:.2f}",
                ])
    return path
