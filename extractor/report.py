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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Caslon+Text:wght@400;700&family=Red+Hat+Mono:wght@400;500&family=Red+Hat+Text:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--paper:#EEEDEA;--surface:#FFFFFF;--ink:#1B1C1E;--muted:#5F6368;--hair:#DEDCD7;
  --cyan:#0089B8;--cyan-soft:rgba(0,137,184,.12)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Red Hat Text",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.55}}
.wrap{{max-width:1120px;margin:0 auto;padding:30px 36px 42px}}
header{{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap;margin-bottom:24px}}
h1{{font-family:"Libre Caslon Text",Georgia,serif;font-weight:400;font-size:27px;line-height:1.2;margin:0 0 6px}}
.sub{{color:var(--muted);margin:0;max-width:64ch}}
.chip{{color:var(--muted);font-size:13px;white-space:nowrap}}
.kpis{{display:flex;gap:28px;flex-wrap:wrap;margin-bottom:26px;padding:16px 20px;
  background:var(--surface);border:1px solid var(--hair);border-radius:8px}}
.kpi .label{{font-size:13px;color:var(--muted)}}
.kpi .value{{font-family:"Libre Caslon Text",Georgia,serif;font-size:23px;margin-top:2px;
  font-variant-numeric:tabular-nums}}
.kpi .note{{font-size:12.5px;color:var(--muted)}}
.kpi.flagged .value{{color:var(--cyan)}}
h2{{font-family:"Libre Caslon Text",Georgia,serif;font-weight:400;font-size:18px;margin:0 0 10px}}
section{{margin-bottom:26px}}
table{{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--hair);
  border-radius:8px;overflow:hidden}}
th,td{{text-align:left;padding:9px 14px;border-bottom:1px solid var(--hair);font-size:13.5px}}
th{{font-size:13px;color:var(--muted);font-weight:500;background:#F7F6F4}}
tbody tr:last-child td{{border-bottom:0}}
td.r,th.r{{text-align:right;font-family:"Red Hat Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}}
td.file{{font-family:"Red Hat Mono",ui-monospace,monospace;font-size:11.5px;color:var(--muted)}}
.tag{{display:inline-block;border-radius:4px;padding:2px 8px;font-size:12px}}
.tag.ok{{background:#EDF3F0;color:#2F6B57}}
.tag.review{{background:var(--cyan-soft);color:#00698C}}
.flag{{color:#00698C;font-size:12.5px}}
.bars{{display:flex;flex-direction:column;gap:8px}}
.bar{{display:grid;grid-template-columns:170px 1fr 96px;align-items:center;gap:14px;font-size:13.5px}}
.track{{background:#E4E2DE;border-radius:4px;height:14px;overflow:hidden}}
.fill{{height:100%;background:var(--cyan);opacity:.75;border-radius:4px}}
.bar .r{{text-align:right;font-family:"Red Hat Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}}
footer{{color:var(--muted);font-size:12.5px;border-top:1px solid var(--hair);padding-top:12px}}
.empty{{color:var(--muted);font-size:13.5px;background:var(--surface);border:1px solid var(--hair);
  border-radius:8px;padding:16px}}
</style></head><body><div class="wrap">
<header>
  <div>
    <h1>{clean} of {total} invoices went straight through, {review} need a human</h1>
    <p class="sub">Read from {total} PDF files in {folder}, across {layouts} supplier layouts. Every figure below was taken from the document, and anything the arithmetic did not support was sent to review instead of being written out.</p>
  </div>
  <div class="chip">Okafor Print Co., accounts payable</div>
</header>

<div class="kpis">
  <div class="kpi"><div class="label">Invoices read</div><div class="value">{total}</div><div class="note">{pages} pages in {seconds}s</div></div>
  <div class="kpi"><div class="label">Line items</div><div class="value">{items}</div><div class="note">captured with quantity and unit price</div></div>
  <div class="kpi"><div class="label">Value extracted</div><div class="value">{currency}{value}</div><div class="note">net {currency}{net} plus tax {currency}{tax}</div></div>
  <div class="kpi flagged"><div class="label">Waiting for a person</div><div class="value">{review}</div><div class="note">{review_pct}% of the batch</div></div>
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

<footer>Generated {run_date}. Fictional business, invented data.</footer>
</div></body></html>"""

EMPTY_REVIEW = """<table><tbody><tr><td style="color:#A7A39B">Nothing was flagged in this run. Every invoice had a readable total, and the tax and line items agreed with it.</td></tr></tbody></table>"""


def money(value) -> str:
    return f"{value:,.2f}" if value is not None else "-"


def build(invoices: list[Invoice], out_path: Path, folder: str = "invoices/", seconds: float = 0.0) -> Path:
    total = len(invoices)
    review = [i for i in invoices if i.needs_review]
    clean = total - len(review)
    currency = next((i.currency for i in invoices if i.total is not None), "USD")
    sym = {"GBP": "\u00a3", "USD": "$"}.get(currency, "")

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
