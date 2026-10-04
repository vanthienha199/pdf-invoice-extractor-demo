"""Read an invoice PDF and pull out the fields, with a confidence score.

The parser does not assume one supplier template. It looks for the shapes that
survive across layouts: a reference that looks like an invoice number, a date
near a date word, money columns at the end of a line, and amounts anchored to
their label. Every answer carries a reason, and anything the arithmetic does not
support is sent to a review queue rather than written out as if it were certain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pdfplumber

MONEY = r"(-?[\d,]+\.\d{2})"
LINE_ITEM = re.compile(rf"^(?P<desc>.+?)\s+(?P<qty>\d{{1,4}})\s+{MONEY}\s+{MONEY}$")
NUMBER = re.compile(r"\b(INV[-\s]?\d{4,})\b", re.I)
AMOUNT = re.compile(MONEY)

# Each label is matched, then the first amount after it on the same line is taken.
# Order matters: the most specific wording wins, so "total due" beats a bare "total"
# and "subtotal" can never be mistaken for the amount payable.
TOTAL_LABELS = [r"total\s+due", r"amount\s+payable", r"\btotal\b"]
NET_LABELS = [r"subtotal", r"\bnet\b"]
TAX_LABELS = [r"sales\s+tax", r"\bvat\b", r"\btax\b"]

SKIP_IN_DESCRIPTION = ("subtotal", "total", "vat", "tax", "invoice", "amount payable")

DATE_PATTERNS = [
    ("%d/%m/%Y", re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")),
    ("%Y-%m-%d", re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")),
    ("%d %B %Y", re.compile(r"\b(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})\b")),
]

GENERIC_HEADINGS = {"invoice", "tax invoice", "bill", "statement", "receipt"}


def to_float(text: str) -> float:
    return float(text.replace(",", ""))


@dataclass
class LineItem:
    description: str
    quantity: int
    unit_price: float
    amount: float


@dataclass
class Invoice:
    source_file: str
    vendor: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    currency: str = "USD"
    net: float | None = None
    tax: float | None = None
    total: float | None = None
    pages: int = 0
    line_items: list[LineItem] = field(default_factory=list)
    confidence: float = 0.0
    flags: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return self.confidence < 0.80 or bool(self.flags)

    def as_row(self) -> dict:
        return {
            "source_file": self.source_file,
            "vendor": self.vendor,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "currency": self.currency,
            "net": self.net,
            "tax": self.tax,
            "total": self.total,
            "line_items": len(self.line_items),
            "pages": self.pages,
            "confidence": round(self.confidence, 2),
            "needs_review": "yes" if self.needs_review else "no",
            "flags": "; ".join(self.flags),
        }


def normalise_date(text: str) -> str:
    for fmt, pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(1), fmt).date().isoformat()
        except ValueError:
            continue
    return ""


RATE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|percent\b)", re.I)


def amount_after_label(lines: list[str], labels: list[str]) -> float | None:
    """First amount that appears after one of these labels on the same line.

    A rate written between the label and the figure is removed first. This
    matters because a sales tax rate such as "10.30%" has the same shape as an
    amount, so a parser that simply takes the next number reads the rate as the
    tax and every total stops reconciling.
    """
    for label in labels:
        anchor = re.compile(label, re.I)
        for line in lines:
            if label == r"\btotal\b" and re.search(r"sub\s*total", line, re.I):
                continue
            match = anchor.search(line)
            if not match:
                continue
            tail = RATE.sub(" ", line[match.end():])
            money = AMOUNT.search(tail)
            if money:
                return to_float(money.group(1))
    return None


def vendor_from_page(page) -> str:
    """The supplier name is the top left block, not the big word INVOICE on the right."""
    words = [w for w in page.extract_words() if w["top"] < page.height * 0.12 and w["x0"] < page.width * 0.5]
    if not words:
        return ""
    top = min(w["top"] for w in words)
    first_line = [w for w in words if abs(w["top"] - top) < 6]
    name = " ".join(w["text"] for w in sorted(first_line, key=lambda w: w["x0"])).strip()
    return name


def parse_line_items(lines: list[str]) -> list[LineItem]:
    items: list[LineItem] = []
    for line in lines:
        match = LINE_ITEM.match(line.strip())
        if not match:
            continue
        desc = match.group("desc").strip()
        if any(w in desc.lower() for w in SKIP_IN_DESCRIPTION):
            continue
        qty = int(match.group("qty"))
        unit = to_float(match.group(3))
        amount = to_float(match.group(4))
        if abs(qty * unit - amount) > 0.02:
            continue
        items.append(LineItem(desc, qty, unit, amount))
    return items


def parse(path: Path) -> Invoice:
    path = Path(path)
    invoice = Invoice(source_file=path.name)

    with pdfplumber.open(path) as pdf:
        invoice.pages = len(pdf.pages)
        page_texts = [(page.extract_text() or "") for page in pdf.pages]
        vendor = vendor_from_page(pdf.pages[0]) if pdf.pages else ""

    text = "\n".join(page_texts)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # A multi page invoice carries a running subtotal on every page and the real
    # totals only on the last one, so totals are read from the last page alone.
    last_page_lines = [l.strip() for l in page_texts[-1].splitlines() if l.strip()]

    if len("".join(lines)) < 40:
        invoice.flags.append("no text layer, this looks like a scan and needs OCR or manual entry")
        invoice.confidence = 0.0
        return invoice

    # Some suppliers print their name in block capitals. Normalising it means a
    # buyer can group by vendor without the same company appearing twice.
    invoice.vendor = vendor.title() if vendor.isupper() else vendor
    if not invoice.vendor or invoice.vendor.lower() in GENERIC_HEADINGS or len(invoice.vendor) > 60:
        invoice.vendor = invoice.vendor or ""
        invoice.flags.append("vendor name not confidently identified")

    found = NUMBER.search(text)
    invoice.invoice_number = found.group(1).replace(" ", "-").upper() if found else ""
    if not invoice.invoice_number:
        invoice.flags.append("no invoice number found")

    date_line = next((l for l in lines if re.search(r"date|dated", l, re.I)), "")
    invoice.invoice_date = normalise_date(date_line) or normalise_date(text)
    if not invoice.invoice_date:
        invoice.flags.append("invoice date could not be read")

    if "£" in text or "gbp" in text.lower():
        invoice.currency = "GBP"
    elif "$" in text or "usd" in text.lower():
        invoice.currency = "USD"

    invoice.total = amount_after_label(last_page_lines, TOTAL_LABELS)
    invoice.net = amount_after_label(last_page_lines, NET_LABELS)
    invoice.tax = amount_after_label(last_page_lines, TAX_LABELS)
    invoice.line_items = parse_line_items(lines)

    score = 0.0
    if invoice.vendor and invoice.vendor.lower() not in GENERIC_HEADINGS:
        score += 0.15
    if invoice.invoice_number:
        score += 0.15
    if invoice.invoice_date:
        score += 0.15
    if invoice.total is not None:
        score += 0.15
    if invoice.line_items:
        score += 0.10

    if None not in (invoice.net, invoice.tax, invoice.total):
        if abs(invoice.net + invoice.tax - invoice.total) <= 0.02:
            score += 0.20
        else:
            invoice.flags.append(
                f"net {invoice.net:.2f} plus tax {invoice.tax:.2f} does not equal total {invoice.total:.2f}"
            )
    else:
        invoice.flags.append("one of net, tax or total is missing")

    if invoice.line_items and invoice.net is not None:
        line_sum = round(sum(i.amount for i in invoice.line_items), 2)
        if abs(line_sum - invoice.net) <= 0.02:
            score += 0.10
        else:
            invoice.flags.append(f"line items add to {line_sum:.2f}, the invoice says net {invoice.net:.2f}")

    invoice.confidence = min(score, 1.0)
    return invoice


def parse_folder(folder: Path) -> list[Invoice]:
    return [parse(p) for p in sorted(Path(folder).glob("*.pdf"))]
