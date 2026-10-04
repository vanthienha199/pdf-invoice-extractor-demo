"""A single file HTML summary of an extraction run, dark by default."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .parse import Invoice

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Invoice extraction, {run_date}</title>
<style>
:root{{--canvas:#15171B;--surface:#1E2126;--line:#2B2F35;--ink:#F3EFE7;--muted:#A7A39B;--accent:#F2994A;--ok:#5FB49C;--warn:#E0A458}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--canvas);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:32px 40px 44px}}
header{{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap;margin-bottom:26px}}
h1{{font-family:"Bricolage Grotesque","IBM Plex Sans",sans-serif;font-weight:800;font-size:30px;letter-spacing:-.02em;line-height:1.1;margin:0 0 6px}}
h1 em{{font-style:normal;color:var(--accent)}}
.sub{{color:var(--muted);margin:0;max-width:64ch}}
.chip{{border:1px solid #3A3F46;color:var(--muted);border-radius:999px;padding:5px 13px;font-size:12px;white-space:nowrap}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:26px}}
.kpi{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px 20px}}
.kpi .label{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}}
.kpi .value{{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:27px;margin-top:6px;font-variant-numeric:tabular-nums}}
.kpi .note{{font-size:12px;color:var(--muted);margin-top:2px}}
.kpi.flagged .value{{color:var(--accent)}}
h2{{font-family:"Bricolage Grotesque","IBM Plex Sans",sans-serif;font-weight:800;font-size:18px;margin:0 0 12px}}
section{{margin-bottom:26px}}
table{{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
th,td{{text-align:left;padding:9px 14px;border-bottom:1px solid var(--line);font-size:13px}}
th{{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);background:#191C21}}
tbody tr:last-child td{{border-bottom:0}}
td.r,th.r{{text-align:right;font-family:"JetBrains Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}}
td.file{{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11.5px;color:var(--muted)}}
.tag{{display:inline-block;border-radius:5px;padding:2px 8px;font-size:11px;font-weight:600}}
.tag.ok{{background:rgba(95,180,156,.16);color:var(--ok)}}
.tag.review{{background:rgba(242,153,74,.16);color:var(--accent)}}
.flag{{color:var(--warn);font-size:12px}}
.bars{{display:flex;flex-direction:column;gap:8px}}
.bar{{display:grid;grid-template-columns:170px 1fr 92px;align-items:center;gap:14px;font-size:13px}}
.track{{background:#23272D;border-radius:5px;height:16px;overflow:hidden}}
.fill{{height:100%;background:var(--accent);opacity:.85;border-radius:5px}}
footer{{color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:14px}}
</style></head><body><div class="wrap">
<header>
  <div>
    <h1>{clean} of {total} invoices went straight through, <em>{review} need a human</em></h1>
    <p class="sub">Read from {total} PDF files in {folder}, across {layouts} supplier layouts. Every figure below was taken from the document, and anything the arithmetic did not support was sent to review instead of being written out.</p>
  </div>
  <div class="chip">Sample project, invented suppliers</div>
</header>

<div class="kpis">
  <div class="kpi"><div class="label">Invoices read</div><div class="value">{total}</div><div class="note">{pages} pages in {seconds}s</div></div>
  <div class="kpi"><div class="label">Line items</div><div class="value">{items}</div><div class="note">captured with quantity and unit price</div></div>
  <div class="kpi"><div class="label">Value extracted</div><div class="value">{currency}{value}</div><div class="note">net {currency}{net} plus tax {currency}{tax}</div></div>
  <div class="kpi flagged"><div class="label">Needs review</div><div class="value">{review}</div><div class="note">{review_pct}% of the batch</div></div>
</div>

<section>
  <h2>Flagged for review</h2>
  {review_table}
</section>

<section>
  <h2>Spend by supplier</h2>
  <div class="bars">{bars}</div>
</section>

<section>
  <h2>Every invoice</h2>
  <table>
    <thead><tr><th>File</th><th>Supplier</th><th>Number</th><th>Date</th><th class="r">Net</th><th class="r">Tax</th><th class="r">Total</th><th class="r">Items</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>

<footer>Generated {run_date}. Built by Ha Le as a portfolio sample. Suppliers, amounts and documents are invented for this demo.</footer>
</div></body></html>"""

EMPTY_REVIEW = """<table><tbody><tr><td style="color:#A7A39B">Nothing was flagged in this run. Every invoice had a readable total, and the tax and line items agreed with it.</td></tr></tbody></table>"""


def money(value) -> str:
    return f"{value:,.2f}" if value is not None else "-"


def build(invoices: list[Invoice], out_path: Path, folder: str = "invoices/", seconds: float = 0.0) -> Path:
    total = len(invoices)
    review = [i for i in invoices if i.needs_review]
    clean = total - len(review)
    currency = next((i.currency for i in invoices if i.total is not None), "GBP")
    sym = "£" if currency == "GBP" else ""

    rows = []
    for i in invoices:
        tag = '<span class="tag review">review</span>' if i.needs_review else '<span class="tag ok">clean</span>'
        rows.append(
            f'<tr><td class="file">{i.source_file}</td><td>{i.vendor or "not read"}</td>'
            f'<td>{i.invoice_number or "-"}</td><td>{i.invoice_date or "-"}</td>'
            f'<td class="r">{money(i.net)}</td><td class="r">{money(i.tax)}</td>'
            f'<td class="r">{money(i.total)}</td><td class="r">{len(i.line_items)}</td><td>{tag}</td></tr>'
        )

    if review:
        review_rows = "".join(
            f'<tr><td class="file">{i.source_file}</td><td>{i.vendor or "not read"}</td>'
            f'<td class="r">{i.confidence:.2f}</td><td class="flag">{"; ".join(i.flags)}</td></tr>'
            for i in review
        )
        review_table = (
            '<table><thead><tr><th>File</th><th>Supplier</th><th class="r">Confidence</th>'
            f"<th>Why it stopped</th></tr></thead><tbody>{review_rows}</tbody></table>"
        )
    else:
        review_table = EMPTY_REVIEW

    by_vendor = defaultdict(float)
    for i in invoices:
        if i.total is not None and i.vendor:
            by_vendor[i.vendor] += i.total
    top = max(by_vendor.values()) if by_vendor else 1
    bars = "".join(
        f'<div class="bar"><div>{name}</div><div class="track"><div class="fill" style="width:{value / top * 100:.0f}%"></div></div>'
        f'<div class="r" style="text-align:right;font-family:JetBrains Mono,monospace">{sym}{money(value)}</div></div>'
        for name, value in sorted(by_vendor.items(), key=lambda kv: -kv[1])
    )

    html = PAGE.format(
        run_date=datetime.now().strftime("%d %B %Y at %H:%M"),
        total=total, clean=clean, review=len(review),
        review_pct=round(len(review) / total * 100) if total else 0,
        pages=sum(i.pages for i in invoices),
        items=sum(len(i.line_items) for i in invoices),
        seconds=f"{seconds:.1f}",
        currency=sym,
        value=money(sum(i.total or 0 for i in invoices)),
        net=money(sum(i.net or 0 for i in invoices)),
        tax=money(sum(i.tax or 0 for i in invoices)),
        folder=folder,
        layouts=4,
        rows="".join(rows),
        review_table=review_table,
        bars=bars,
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
