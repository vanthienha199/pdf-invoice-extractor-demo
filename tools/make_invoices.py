"""Generate the sample invoice PDFs.

Every vendor, address and number here is invented for this demo. Four different
layouts, because real suppliers never agree on one, plus a two page invoice and
one that is a flat image with no text layer, which is what a scan looks like to
a parser. That last one is there on purpose: the extractor should flag it for a
human rather than guess.
"""

from __future__ import annotations

import random
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

random.seed(7)

OUT = Path(__file__).resolve().parent.parent / "invoices"
BUYER = ["Fernleaf Studio", "18 Alder Court", "Blue Harbor BH4 2QT"]

VENDORS = [
    ("Oakline Paper Co", "Unit 7 Mill Road, Northgate NG1 4PS", "GB", 0.20),
    ("Brightwater Utilities", "PO Box 221, Westfield WF9 3LD", "GB", 0.05),
    ("Tern Logistics", "Dock 3, Harbour Way, Blue Harbor BH1 7RT", "GB", 0.20),
    ("Nine Yards Print", "44 Foundry Street, Kelsey KY2 8AA", "GB", 0.20),
    ("Marlow Coffee Supply", "2 Granary Lane, Thornbury TH5 1BE", "GB", 0.00),
    ("Quayside IT Services", "Suite 12, Pier House, Blue Harbor BH2 9GG", "GB", 0.20),
]

ITEMS = [
    ("Recycled A4 paper, 80gsm, box of 5 reams", 5, 24.50),
    ("Business cards, 400gsm matt, 500", 1, 68.00),
    ("Courier, next day, up to 10kg", 3, 11.75),
    ("Office electricity, standing charge", 1, 42.10),
    ("Coffee beans, 1kg, house blend", 6, 18.40),
    ("Managed backup, per seat", 12, 4.25),
    ("Poster print, A1, satin", 8, 9.60),
    ("Pallet delivery, local", 1, 95.00),
    ("Toner cartridge, black, high yield", 2, 71.30),
    ("Support hours, out of hours rate", 4, 85.00),
    ("Envelopes, C4 window, box of 250", 3, 16.75),
    ("Water cooler refill, 18 litre", 4, 7.90),
]

DATES = [
    "03/01/2026", "11 January 2026", "2026-01-19", "27/01/2026", "02 February 2026",
    "2026-02-08", "14/02/2026", "21 February 2026", "2026-03-02", "09/03/2026",
    "16 March 2026", "2026-03-24", "31/03/2026", "07 April 2026", "2026-04-13",
    "20/04/2026", "28 April 2026", "2026-05-05", "12/05/2026", "19 May 2026",
]


def money(value: float) -> str:
    return f"{value:,.2f}"


def pick_items(n: int) -> list[tuple[str, int, float]]:
    rows = random.sample(ITEMS, n)
    return [(d, q, p) for d, q, p in rows]


def totals(rows, vat_rate):
    net = sum(q * p for _, q, p in rows)
    vat = round(net * vat_rate, 2)
    return round(net, 2), vat, round(net + vat, 2)


def layout_classic(c, meta, rows, page_items=None):
    """Label on the left, value on the right. The most common shape."""
    v = meta["vendor"]
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, 272 * mm, v[0])
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, 266 * mm, v[1])

    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(190 * mm, 272 * mm, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawRightString(190 * mm, 264 * mm, f"Invoice number: {meta['number']}")
    c.drawRightString(190 * mm, 259 * mm, f"Invoice date: {meta['date']}")
    c.drawRightString(190 * mm, 254 * mm, f"Due date: {meta['due']}")

    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, 240 * mm, "Bill to")
    c.setFont("Helvetica", 9)
    for i, line in enumerate(BUYER):
        c.drawString(20 * mm, (235 - i * 4.5) * mm, line)

    y = 212
    c.setFont("Helvetica-Bold", 9)
    for label, x in (("Description", 20), ("Qty", 128), ("Unit price", 150), ("Amount", 190)):
        (c.drawRightString if x > 120 else c.drawString)(x * mm, y * mm, label)
    c.setStrokeColor(colors.HexColor("#999999"))
    c.line(20 * mm, (y - 2) * mm, 190 * mm, (y - 2) * mm)

    c.setFont("Helvetica", 9)
    y -= 8
    for desc, qty, price in rows:
        c.drawString(20 * mm, y * mm, desc[:62])
        c.drawRightString(128 * mm, y * mm, str(qty))
        c.drawRightString(150 * mm, y * mm, money(price))
        c.drawRightString(190 * mm, y * mm, money(qty * price))
        y -= 6

    net, vat, gross = meta["totals"]
    y -= 6
    c.line(120 * mm, (y + 4) * mm, 190 * mm, (y + 4) * mm)
    c.drawRightString(150 * mm, y * mm, "Subtotal")
    c.drawRightString(190 * mm, y * mm, money(net))
    y -= 6
    c.drawRightString(150 * mm, y * mm, f"VAT @ {int(meta['vat_rate'] * 100)}%")
    c.drawRightString(190 * mm, y * mm, money(vat))
    y -= 7
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(150 * mm, y * mm, "Total due")
    c.drawRightString(190 * mm, y * mm, f"GBP {money(gross)}")


def layout_compact(c, meta, rows, page_items=None):
    """Everything crammed at the top, totals inline, different wording."""
    v = meta["vendor"]
    c.setFont("Helvetica-Bold", 13)
    c.drawString(18 * mm, 278 * mm, v[0].upper())
    c.setFont("Helvetica", 8)
    c.drawString(18 * mm, 273 * mm, v[1])
    c.drawString(18 * mm, 268 * mm, f"Tax invoice {meta['number']}   Dated {meta['date']}")
    c.drawString(18 * mm, 263 * mm, "Customer: Fernleaf Studio")

    y = 250
    c.setFont("Helvetica-Bold", 8)
    c.drawString(18 * mm, y * mm, "Item")
    c.drawRightString(140 * mm, y * mm, "Units")
    c.drawRightString(165 * mm, y * mm, "Rate")
    c.drawRightString(192 * mm, y * mm, "Line total")
    c.setFont("Helvetica", 8)
    y -= 6
    for desc, qty, price in rows:
        c.drawString(18 * mm, y * mm, desc[:68])
        c.drawRightString(140 * mm, y * mm, str(qty))
        c.drawRightString(165 * mm, y * mm, money(price))
        c.drawRightString(192 * mm, y * mm, money(qty * price))
        y -= 5.2

    net, vat, gross = meta["totals"]
    y -= 8
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, y * mm, f"Net {money(net)}    Tax {money(vat)}")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(192 * mm, y * mm, f"AMOUNT PAYABLE GBP {money(gross)}")


def layout_boxed(c, meta, rows, page_items=None):
    """Header in a filled box, totals in a box too."""
    v = meta["vendor"]
    c.setFillColor(colors.HexColor("#22303a"))
    c.rect(0, 258 * mm, 210 * mm, 39 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(18 * mm, 283 * mm, v[0])
    c.setFont("Helvetica", 8)
    c.drawString(18 * mm, 277 * mm, v[1])
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(192 * mm, 283 * mm, f"Invoice {meta['number']}")
    c.setFont("Helvetica", 9)
    c.drawRightString(192 * mm, 277 * mm, f"Date of issue {meta['date']}")
    c.drawRightString(192 * mm, 271 * mm, f"Payment due {meta['due']}")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, 248 * mm, "Invoice to Fernleaf Studio, 18 Alder Court, Blue Harbor BH4 2QT")

    y = 232
    c.setFont("Helvetica-Bold", 9)
    c.drawString(18 * mm, y * mm, "Goods or service")
    c.drawRightString(132 * mm, y * mm, "Quantity")
    c.drawRightString(160 * mm, y * mm, "Price each")
    c.drawRightString(192 * mm, y * mm, "Net")
    c.setFont("Helvetica", 9)
    y -= 7
    for desc, qty, price in rows:
        c.drawString(18 * mm, y * mm, desc[:60])
        c.drawRightString(132 * mm, y * mm, str(qty))
        c.drawRightString(160 * mm, y * mm, money(price))
        c.drawRightString(192 * mm, y * mm, money(qty * price))
        y -= 6

    net, vat, gross = meta["totals"]
    y -= 10
    c.setStrokeColor(colors.HexColor("#22303a"))
    c.rect(120 * mm, (y - 14) * mm, 72 * mm, 26 * mm, stroke=1, fill=0)
    c.setFont("Helvetica", 9)
    c.drawString(124 * mm, (y + 6) * mm, "Subtotal")
    c.drawRightString(188 * mm, (y + 6) * mm, money(net))
    c.drawString(124 * mm, y * mm, f"VAT {int(meta['vat_rate'] * 100)} percent")
    c.drawRightString(188 * mm, y * mm, money(vat))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(124 * mm, (y - 8) * mm, "Total")
    c.drawRightString(188 * mm, (y - 8) * mm, f"GBP {money(gross)}")


def layout_scan(c, meta, rows, page_items=None):
    """A flat image with no text layer, which is what a scan gives a parser."""
    import io

    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader

    def font(size, bold=False):
        name = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    width, height = 1240, 1754
    img = Image.new("RGB", (width, height), "#f4f2ed")
    d = ImageDraw.Draw(img)
    v = meta["vendor"]
    d.text((90, 95), v[0], font=font(44, True), fill="#1c1c1c")
    d.text((90, 150), v[1], font=font(20), fill="#333333")
    d.text((90, 225), f"INVOICE {meta['number']}", font=font(28, True), fill="#1c1c1c")
    d.text((90, 268), f"Date {meta['date']}", font=font(20), fill="#333333")
    d.text((90, 300), "Customer: Fernleaf Studio", font=font(20), fill="#333333")

    y = 380
    for desc, qty, price in rows:
        d.text((90, y), f"{qty} x {desc[:46]}", font=font(19), fill="#1c1c1c")
        d.text((980, y), money(qty * price), font=font(19), fill="#1c1c1c")
        y += 40

    net, vat, gross = meta["totals"]
    d.text((700, y + 50), f"Subtotal {money(net)}", font=font(20), fill="#1c1c1c")
    d.text((700, y + 90), f"VAT {money(vat)}", font=font(20), fill="#1c1c1c")
    d.text((700, y + 140), f"TOTAL GBP {money(gross)}", font=font(26, True), fill="#1c1c1c")

    # a scan is never perfectly straight or perfectly clean
    img = img.rotate(-0.6, resample=Image.BICUBIC, fillcolor="#f4f2ed")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), 0, 0, width=210 * mm, height=297 * mm)


LAYOUTS = [layout_classic, layout_compact, layout_boxed]


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path in OUT.glob("*.pdf"):
        path.unlink()

    manifest = []
    for i in range(20):
        vendor = VENDORS[i % len(VENDORS)]
        n_items = random.choice([2, 3, 3, 4, 5])
        rows = pick_items(n_items)
        vat_rate = vendor[3]
        meta = {
            "vendor": vendor,
            "number": f"INV-{2026}{i + 101}",
            "date": DATES[i],
            "due": "30 days from invoice date",
            "vat_rate": vat_rate,
            "totals": totals(rows, vat_rate),
        }

        two_page = i == 11
        scanned = i == 6
        if two_page:
            rows = pick_items(5) + pick_items(4)
            meta["totals"] = totals(rows, vat_rate)

        name = f"{vendor[0].lower().replace(' ', '-')}-{meta['number'].lower()}.pdf"
        c = pdfcanvas.Canvas(str(OUT / name), pagesize=A4)
        if scanned:
            layout_scan(c, meta, rows[:4])
        elif two_page:
            first, second = rows[:5], rows[5:]
            layout_classic(c, {**meta, "totals": totals(first, vat_rate)}, first)
            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(105 * mm, 15 * mm, "Continued on page 2 of 2")
            c.showPage()
            layout_classic(c, meta, second)
            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(105 * mm, 15 * mm, "Page 2 of 2")
        else:
            LAYOUTS[i % len(LAYOUTS)](c, meta, rows)
        c.save()

        manifest.append({
            "file": name, "vendor": vendor[0], "number": meta["number"], "date": meta["date"],
            "net": meta["totals"][0], "vat": meta["totals"][1], "gross": meta["totals"][2],
            "lines": len(rows), "scanned": scanned, "pages": 2 if two_page else 1,
        })

    import json
    (OUT.parent / "tests" / "expected.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(manifest)} invoices written to {OUT.name}/")
    print(f"  one scanned image only: {[m['file'] for m in manifest if m['scanned']][0]}")
    print(f"  one across two pages:   {[m['file'] for m in manifest if m['pages'] == 2][0]}")


if __name__ == "__main__":
    build()
