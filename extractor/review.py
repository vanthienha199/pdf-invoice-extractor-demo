"""Build the review view: the invoice on the left, what was read on the right.

Each page is rendered to PNG once so the browser can show the real document
rather than a description of it, and every extracted value carries the box it
came from, so hovering a field outlines its spot on the page.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .parse import Invoice

DPI = 130
SCALE = DPI / 72.0

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Okafor Print Co., supplier invoices</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Caslon+Text:wght@400;700&family=Red+Hat+Mono:wght@400;500&family=Red+Hat+Text:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#EEEDEA; --surface:#FFFFFF; --ink:#1B1C1E; --muted:#5F6368;
  --hair:#DEDCD7; --cyan:#0089B8; --cyan-soft:rgba(0,137,184,.12);
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Red Hat Text",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.5}
.shell{max-width:1360px;margin:0 auto;padding:26px 32px 34px}
header{display:flex;justify-content:space-between;align-items:baseline;gap:24px;flex-wrap:wrap;margin-bottom:18px}
.shop{font-family:"Libre Caslon Text",Georgia,serif;font-size:25px;margin:0}
.shop span{color:var(--muted);font-family:"Red Hat Text",sans-serif;font-size:14px;margin-left:10px}
.counts{color:var(--muted);font-size:14px}
.counts b{color:var(--ink);font-weight:600}

.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px}
select{font:inherit;padding:7px 10px;border:1px solid var(--hair);border-radius:6px;background:var(--surface);color:var(--ink);min-width:320px}
.btn{font:inherit;font-weight:600;padding:7px 15px;border-radius:6px;border:1px solid var(--cyan);
  background:var(--cyan);color:#fff;cursor:pointer;transition:background .15s ease-out}
.btn:hover{background:#00769e}
.btn.quiet{background:transparent;color:var(--cyan)}
.btn.quiet:hover{background:var(--cyan-soft)}

.split{display:grid;grid-template-columns:minmax(0,1fr) 430px;gap:22px;align-items:start}
.doc{background:var(--surface);border:1px solid var(--hair);border-radius:8px;padding:14px;position:relative;
  max-height:calc(100vh - 215px);overflow:auto}
.pagewrap{position:relative;line-height:0}
.pagewrap+.pagewrap{margin-top:14px}
.pagewrap img{width:100%;height:auto;border:1px solid var(--hair)}
.mark{position:absolute;border:2px solid transparent;border-radius:3px;pointer-events:none;
  transition:border-color .18s ease-out,background-color .18s ease-out}
.mark.on{border-color:var(--cyan);background:var(--cyan-soft)}
.mark.on.check{border-style:dashed}

.panel{background:var(--surface);border:1px solid var(--hair);border-radius:8px;padding:18px 20px}
.panel h2{font-family:"Libre Caslon Text",Georgia,serif;font-size:17px;margin:0 0 2px;font-weight:400}
.panel .sub{color:var(--muted);font-size:13px;margin:0 0 14px}
.field{display:grid;grid-template-columns:118px minmax(0,1fr);gap:10px;padding:8px 10px;margin:0 -10px;
  border-radius:6px;cursor:default;transition:background-color .18s ease-out}
.field:hover{background:var(--cyan-soft)}
.field .k{color:var(--muted);font-size:13.5px}
.field .v{font-family:"Red Hat Mono",ui-monospace,monospace;font-size:13.5px;word-break:break-word}
.field .v.num{text-align:right;font-variant-numeric:tabular-nums}
.field.check .v{border-bottom:1px dashed var(--cyan);padding-bottom:1px}
.field .note{grid-column:2;color:var(--muted);font-size:12.5px;font-family:"Red Hat Text",sans-serif}
.total .k,.total .v{font-family:"Libre Caslon Text",Georgia,serif;font-size:17px;color:var(--ink)}
.total .v{font-variant-numeric:tabular-nums}
.rule{border:0;border-top:1px solid var(--hair);margin:12px 0}
h3{font-size:13.5px;font-weight:600;margin:0 0 6px;color:var(--muted)}
.items{width:100%;border-collapse:collapse}
.items td{padding:5px 0;border-bottom:1px solid var(--hair);font-size:13px;vertical-align:top}
.items tr:last-child td{border-bottom:0}
.items td.q,.items td.a{font-family:"Red Hat Mono",ui-monospace,monospace;text-align:right;
  font-variant-numeric:tabular-nums;white-space:nowrap;padding-left:10px}
.items tr{cursor:default;transition:background-color .18s ease-out}
.items tr:hover{background:var(--cyan-soft)}

.state{background:var(--surface);border:1px solid var(--hair);border-radius:8px;padding:26px 24px;text-align:left}
.state h2{font-family:"Libre Caslon Text",Georgia,serif;font-size:19px;margin:0 0 6px;font-weight:400}
.state p{color:var(--muted);margin:0 0 14px;max-width:46ch}
footer{color:var(--muted);font-size:12.5px;margin-top:22px;border-top:1px solid var(--hair);padding-top:12px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head><body>
<div class="shell">
  <header>
    <h1 class="shop">Okafor Print Co.<span>supplier invoices, read and checked</span></h1>
    <div class="counts" id="counts"></div>
  </header>

  <div class="bar">
    <select id="pick"></select>
    <button class="btn" id="export">Export to Excel</button>
    <button class="btn quiet" id="next">Next needing a check</button>
  </div>

  <div class="split">
    <div class="doc" id="doc"></div>
    <div id="side"></div>
  </div>

  <footer>Fictional business, invented data.</footer>
</div>
<script src="data.js"></script>
<script src="app.js"></script>
</body></html>"""

APP_JS = """const money = (v, c) => v === null || v === undefined ? "not read" : (c === "GBP" ? "\\u00a3" : "$") + v.toFixed(2);
const esc = (s) => String(s).replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));

const pick = document.getElementById("pick");
const doc = document.getElementById("doc");
const side = document.getElementById("side");
const counts = document.getElementById("counts");

const clean = INVOICES.filter((i) => !i.needs_review).length;
counts.innerHTML = `<b>${INVOICES.length}</b> invoices read, <b>${clean}</b> went straight through,
  <b>${INVOICES.length - clean}</b> waiting for a person`;

INVOICES.forEach((inv, index) => {
  const option = document.createElement("option");
  option.value = index;
  option.textContent = `${inv.vendor || "supplier not read"} \\u00b7 ${inv.invoice_number || inv.source_file}`;
  pick.appendChild(option);
});

function drawDocument(inv) {
  doc.innerHTML = inv.pages_png.map((src, page) => {
    const size = inv.page_sizes[page];
    const marks = Object.entries(inv.boxes)
      .filter(([, b]) => b.page === page)
      .map(([name, b]) => mark(name, b, size))
      .join("");
    const items = inv.line_items
      .map((item, n) => item.box && item.box.page === page ? mark(`item-${n}`, item.box, size) : "")
      .join("");
    return `<div class="pagewrap"><img src="${src}" alt="Page ${page + 1} of ${esc(inv.source_file)}">${marks}${items}</div>`;
  }).join("");
}

function mark(name, box, size) {
  const left = (box.x0 / size.width) * 100;
  const top = (box.top / size.height) * 100;
  const width = ((box.x1 - box.x0) / size.width) * 100;
  const height = ((box.bottom - box.top) / size.height) * 100;
  return `<span class="mark" data-mark="${name}" style="left:${left}%;top:${top}%;width:${width}%;height:${height}%"></span>`;
}

function link(row, name, check) {
  row.addEventListener("mouseenter", () => {
    const m = doc.querySelector(`[data-mark="${name}"]`);
    if (m) { m.classList.add("on"); if (check) m.classList.add("check"); }
  });
  row.addEventListener("mouseleave", () => {
    const m = doc.querySelector(`[data-mark="${name}"]`);
    if (m) m.classList.remove("on", "check");
  });
}

function drawPanel(inv) {
  if (inv.error) {
    side.innerHTML = `<div class="state"><h2>Nothing to read on this one</h2>
      <p>${esc(inv.error)}</p>
      <p>It is kept in the batch and listed in the spreadsheet so it cannot be quietly dropped.</p>
      <button class="btn quiet" id="skip">Next invoice</button></div>`;
    document.getElementById("skip").onclick = () => select(Number(pick.value) + 1);
    return;
  }

  const fields = [
    ["Supplier", "vendor", inv.vendor || "not read", false],
    ["Invoice number", "invoice_number", inv.invoice_number || "not read", false],
    ["Invoice date", "invoice_date", inv.invoice_date || "not read", false],
    ["Net", "net", money(inv.net, inv.currency), true],
    ["Sales tax", "tax", money(inv.tax, inv.currency), true],
  ];

  const rows = fields.map(([label, key, value, num]) => {
    const note = inv.notes[key];
    return `<div class="field${note ? " check" : ""}" data-field="${key}">
      <div class="k">${label}</div><div class="v${num ? " num" : ""}">${esc(value)}</div>
      ${note ? `<div class="note">Check: ${esc(note)}</div>` : ""}</div>`;
  }).join("");

  const items = inv.line_items.map((item, n) => `<tr data-item="${n}">
      <td>${esc(item.description)}</td><td class="q">${item.quantity}</td>
      <td class="a">${money(item.amount, inv.currency)}</td></tr>`).join("");

  side.innerHTML = `<div class="panel">
    <h2>What was read</h2>
    <p class="sub">In the order the invoice prints it. Hover a value to see where it sits on the page.</p>
    ${rows}
    <div class="field total" data-field="total"><div class="k">Total</div>
      <div class="v num">${money(inv.total, inv.currency)}</div></div>
    <hr class="rule">
    <h3>Line items</h3>
    <table class="items"><tbody>${items || '<tr><td colspan="3">No line items on this invoice.</td></tr>'}</tbody></table>
  </div>`;

  side.querySelectorAll("[data-field]").forEach((row) =>
    link(row, row.dataset.field, row.classList.contains("check")));
  side.querySelectorAll("[data-item]").forEach((row) => link(row, `item-${row.dataset.item}`, false));
}

function select(index) {
  const i = Math.max(0, Math.min(index, INVOICES.length - 1));
  pick.value = i;
  const inv = INVOICES[i];
  drawDocument(inv);
  drawPanel(inv);
}

pick.addEventListener("change", () => select(Number(pick.value)));
document.getElementById("next").addEventListener("click", () => {
  const from = Number(pick.value);
  const found = INVOICES.findIndex((inv, n) => n > from && (inv.needs_review || Object.keys(inv.notes).length));
  select(found === -1 ? INVOICES.findIndex((inv) => inv.needs_review || Object.keys(inv.notes).length) : found);
});
document.getElementById("export").addEventListener("click", () => {
  window.location.href = "invoices.xlsx";
});

if (!INVOICES.length) {
  document.querySelector(".bar").style.display = "none";
  document.querySelector(".split").innerHTML = `<div class="state">
    <h2>No invoices in this folder yet</h2>
    <p>Drop PDF or image files into the watched folder and run the extractor again.
       Everything it reads lands here, and anything it cannot read is listed rather than skipped.</p></div>`;
} else {
  select(0);
}
"""


def render_pages(pdf: Path, out_dir: Path) -> list[str]:
    stem = pdf.stem
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), str(pdf), str(out_dir / stem)],
                   check=True, capture_output=True)
    return [p.name for p in sorted(out_dir.glob(f"{stem}-*.png"))]


def build(invoices: list[Invoice], out_dir: Path, invoice_dir: Path, xlsx: Path | None = None) -> Path:
    out_dir = Path(out_dir)
    pages_dir = out_dir / "pages"
    shutil.rmtree(pages_dir, ignore_errors=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    payload = []
    for invoice in invoices:
        pdf = Path(invoice_dir) / invoice.source_file
        images = render_pages(pdf, pages_dir) if pdf.exists() else []
        payload.append({
            "source_file": invoice.source_file,
            "vendor": invoice.vendor,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "currency": invoice.currency,
            "net": invoice.net,
            "tax": invoice.tax,
            "total": invoice.total,
            "needs_review": invoice.needs_review,
            "error": invoice.flags[0] if invoice.confidence == 0.0 and invoice.flags else "",
            "notes": invoice.notes,
            "boxes": invoice.boxes,
            "page_sizes": invoice.page_sizes,
            "pages_png": [f"pages/{name}" for name in images],
            "line_items": [
                {"description": i.description, "quantity": i.quantity,
                 "unit_price": i.unit_price, "amount": i.amount,
                 "box": i.box.as_dict() if i.box else None}
                for i in invoice.line_items
            ],
        })

    (out_dir / "index.html").write_text(PAGE, encoding="utf-8")
    (out_dir / "app.js").write_text(APP_JS, encoding="utf-8")
    (out_dir / "data.js").write_text("const INVOICES = " + json.dumps(payload, indent=1) + ";\n", encoding="utf-8")
    if xlsx and Path(xlsx).exists():
        shutil.copy(xlsx, out_dir / "invoices.xlsx")
    return out_dir / "index.html"
