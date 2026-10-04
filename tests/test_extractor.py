import json
from pathlib import Path

import pytest

from extractor.export import to_excel
from extractor.parse import (
    amount_after_label,
    normalise_date,
    parse,
    parse_folder,
    parse_line_items,
)

ROOT = Path(__file__).resolve().parent.parent
INVOICES = ROOT / "invoices"
EXPECTED = json.loads((ROOT / "tests" / "expected.json").read_text())


@pytest.fixture(scope="module")
def parsed():
    return parse_folder(INVOICES)


def test_dates_are_normalised_from_three_written_forms():
    assert normalise_date("Invoice date: 03/01/2026") == "2026-01-03"
    assert normalise_date("Dated 11 January 2026") == "2026-01-11"
    assert normalise_date("Date of issue 2026-01-19") == "2026-01-19"
    assert normalise_date("no date here") == ""


def test_a_rate_between_the_label_and_the_figure_is_skipped():
    assert amount_after_label(["VAT @ 20% 46.91"], [r"\bvat\b"]) == 46.91
    assert amount_after_label(["VAT 20 percent 119.28"], [r"\bvat\b"]) == 119.28


def test_a_two_decimal_rate_is_not_mistaken_for_the_amount():
    """A sales tax rate like 10.30% has the same shape as money."""
    assert amount_after_label(["Sales tax @ 10.30% 76.49"], [r"sales\s+tax"]) == 76.49
    assert amount_after_label(["Sales tax 10.35 percent 84.12"], [r"sales\s+tax"]) == 84.12
    assert amount_after_label(["Net 739.00    Sales tax 76.49"], [r"sales\s+tax"]) == 76.49


def test_currency_is_read_from_the_document(parsed):
    assert {i.currency for i in parsed if i.total is not None} == {"USD"}


def test_subtotal_is_never_mistaken_for_the_total():
    lines = ["Subtotal 234.55", "VAT @ 20% 46.91", "Total due GBP 281.46"]
    assert amount_after_label(lines, [r"total\s+due", r"amount\s+payable", r"\btotal\b"]) == 281.46
    assert amount_after_label(lines, [r"subtotal", r"\bnet\b"]) == 234.55


def test_a_line_whose_maths_does_not_work_is_rejected():
    good = parse_line_items(["Toner cartridge, black 2 71.30 142.60"])
    assert len(good) == 1 and good[0].quantity == 2
    assert parse_line_items(["Toner cartridge, black 2 71.30 999.00"]) == []


def test_every_sample_invoice_is_read(parsed):
    assert len(parsed) == len(EXPECTED) == 20


def test_only_the_scan_is_flagged(parsed):
    review = [i for i in parsed if i.needs_review]
    assert len(review) == 1
    assert review[0].confidence == 0.0
    assert "no text layer" in review[0].flags[0]


def test_totals_match_what_the_documents_say(parsed):
    expected = {e["file"]: e for e in EXPECTED if not e["scanned"]}
    for invoice in parsed:
        if invoice.source_file not in expected:
            continue
        want = expected[invoice.source_file]
        assert invoice.total == pytest.approx(want["gross"], abs=0.01), invoice.source_file
        assert invoice.net == pytest.approx(want["net"], abs=0.01), invoice.source_file
        assert invoice.tax == pytest.approx(want["vat"], abs=0.01), invoice.source_file
        assert invoice.invoice_number == want["number"]


def test_the_two_page_invoice_uses_the_totals_from_the_last_page(parsed):
    want = next(e for e in EXPECTED if e["pages"] == 2)
    invoice = next(i for i in parsed if i.source_file == want["file"])
    assert invoice.pages == 2
    assert invoice.total == pytest.approx(want["gross"], abs=0.01)
    assert sum(i.amount for i in invoice.line_items) == pytest.approx(invoice.net, abs=0.02)
    assert not invoice.needs_review


def test_vendor_names_are_consistent_across_layouts(parsed):
    names = {i.vendor for i in parsed if i.vendor}
    assert "Brightwater Utilities" in names
    assert "BRIGHTWATER UTILITIES" not in names
    assert "INVOICE" not in names


def test_excel_has_both_sheets_and_every_row(tmp_path, parsed):
    from openpyxl import load_workbook

    path = to_excel(parsed, tmp_path / "out.xlsx")
    book = load_workbook(path)
    assert book.sheetnames == ["Invoices", "Line items"]
    assert book["Invoices"].max_row == len(parsed) + 1
    assert book["Line items"].max_row == sum(len(i.line_items) for i in parsed) + 1


def test_a_folder_with_no_pdfs_returns_nothing(tmp_path):
    assert parse_folder(tmp_path) == []
