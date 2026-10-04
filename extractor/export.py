"""Write the extracted invoices to Excel and CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .parse import Invoice

HEADER_FILL = PatternFill("solid", fgColor="1E2126")
HEADER_FONT = Font(color="F3EFE7", bold=True, size=10)
REVIEW_FILL = PatternFill("solid", fgColor="FCEBD8")
MONEY_FMT = "#,##0.00"

INVOICE_COLUMNS = [
    ("source_file", 38), ("vendor", 24), ("invoice_number", 16), ("invoice_date", 13),
    ("currency", 9), ("net", 12), ("tax", 11), ("total", 12), ("line_items", 11),
    ("pages", 7), ("confidence", 11), ("needs_review", 14), ("flags", 60),
]
ITEM_COLUMNS = [
    ("source_file", 38), ("invoice_number", 16), ("vendor", 24), ("description", 52),
    ("quantity", 10), ("unit_price", 12), ("amount", 12),
]


def _style_header(sheet, columns) -> None:
    for index, (name, width) in enumerate(columns, start=1):
        cell = sheet.cell(row=1, column=index, value=name.replace("_", " "))
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"


def to_excel(invoices: list[Invoice], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook()

    sheet = book.active
    sheet.title = "Invoices"
    _style_header(sheet, INVOICE_COLUMNS)
    for row_index, invoice in enumerate(invoices, start=2):
        row = invoice.as_row()
        for col_index, (name, _) in enumerate(INVOICE_COLUMNS, start=1):
            cell = sheet.cell(row=row_index, column=col_index, value=row[name])
            if name in ("net", "tax", "total"):
                cell.number_format = MONEY_FMT
            if name == "confidence":
                cell.number_format = "0.00"
            if invoice.needs_review:
                cell.fill = REVIEW_FILL
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
                if name in ("unit_price", "amount"):
                    cell.number_format = MONEY_FMT
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
