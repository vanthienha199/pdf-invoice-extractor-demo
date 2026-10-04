"""Capture every gallery input from real output.

Nothing here is mocked up. The summary is the file the tool writes, the
spreadsheet is rendered from the real .xlsx by Quick Look, the invoice image is
a real sample PDF rendered by pdftoppm, and the two terminal cards hold the
captured stdout of a real run and a real test pass.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT.parent / "raw"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
PY = str(ROOT / ".venv" / "bin" / "python")

CARD = """<!doctype html>
<html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#F6F3EE;font-family:"IBM Plex Sans",system-ui,sans-serif}}
.card{{margin:34px;background:#FFFEFB;border:1px solid #E4DED3;border-radius:10px;padding:22px 26px;box-shadow:0 1px 2px rgba(0,0,0,.05),0 18px 34px -26px rgba(0,0,0,.4)}}
h3{{margin:0 0 14px;font-size:15px;color:#2A2924}}
pre{{margin:0;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:{size}px;line-height:1.6;color:#2A2924;white-space:pre-wrap}}
b{{color:#111}} .g{{color:#1F7A5C}} .a{{color:#A2621B}} .d{{color:#8A857C}}
</style></head><body><div class="card"><h3>{title}</h3><pre>{body}</pre></div></body></html>"""


def colourise(text: str) -> str:
    out = []
    for line in html.escape(ANSI.sub("", text)).splitlines():
        line = re.sub(r"\bok\b", '<span class="g">ok</span>', line, count=1)
        line = re.sub(r"\breview\b", '<span class="a">review</span>', line, count=1)
        line = re.sub(r"(\d+ need a human)", r'<span class="a">\1</span>', line)
        line = re.sub(r"(passed|PASSED)", r'<span class="g">\1</span>', line)
        line = re.sub(r"^(\s+conf .*)$", r'<span class="d">\1</span>', line)
        out.append(line)
    return "\n".join(out)


def card(title: str, text: str, name: str, size: float = 12.5) -> Path:
    path = RAW / f"{name}.html"
    path.write_text(CARD.format(title=title, body=colourise(text), size=size), encoding="utf-8")
    return path


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    run = subprocess.run([PY, "-m", "extractor.cli", "run", "--input", "invoices", "--out", "out"],
                         cwd=ROOT, capture_output=True, text=True)
    lines = ANSI.sub("", run.stdout).splitlines()
    trimmed = lines[:6] + ["  ..."] + lines[-9:]
    card("Terminal, one command over a folder of PDFs", "\n".join(trimmed), "terminal")

    tests = subprocess.run([PY, "-m", "pytest", "tests", "-v", "--no-header", "-q"],
                           cwd=ROOT, capture_output=True, text=True)
    body = "\n".join(ANSI.sub("", tests.stdout).splitlines()[:26])
    card("Tests, run before every handover", body, "tests", size=11)

    pdf = sorted((ROOT / "invoices").glob("oakline-paper-co-*.pdf"))[0]
    subprocess.run(["pdftoppm", "-png", "-r", "150", "-f", "1", "-l", "1",
                    str(pdf), str(RAW / "invoice_pdf")], check=True)
    for stray in RAW.glob("invoice_pdf-*.png"):
        stray.rename(RAW / "invoice_pdf.png")

    shutil.rmtree(RAW / "_ql", ignore_errors=True)
    (RAW / "_ql").mkdir()
    subprocess.run(["qlmanage", "-t", "-s", "2200", "-o", str(RAW / "_ql"), str(ROOT / "out" / "invoices.xlsx")],
                   capture_output=True, check=False)
    shot = next((RAW / "_ql").glob("*.png"), None)
    if shot:
        shot.rename(RAW / "spreadsheet.png")
    shutil.rmtree(RAW / "_ql", ignore_errors=True)

    print("raw inputs ready in", RAW)
    for path in sorted(RAW.iterdir()):
        print("  ", path.name)


if __name__ == "__main__":
    main()
