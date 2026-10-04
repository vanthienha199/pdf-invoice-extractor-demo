"""Command line entry point: read a folder of invoice PDFs, write a spreadsheet."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from .export import items_to_csv, to_csv, to_excel
from .parse import parse_folder
from .report import build as build_report

ROOT = Path(__file__).resolve().parent.parent

AMBER = "\033[33m"
GREEN = "\033[32m"
DIM = "\033[2m"
BOLD = "\033[1m"
OFF = "\033[0m"


def short(path) -> str:
    try:
        return os.path.relpath(path)
    except ValueError:
        return str(path)


def run(args: argparse.Namespace) -> int:
    folder = Path(args.input)
    if not folder.is_dir():
        raise SystemExit(f"{short(folder)} is not a folder")

    print(f"{BOLD}Invoice extractor{OFF} {DIM}(sample project){OFF}")
    print(f"  reading  {short(folder)}\n")

    started = time.perf_counter()
    invoices = parse_folder(folder)
    seconds = time.perf_counter() - started

    if not invoices:
        print("  no PDF files found")
        return 1

    for invoice in invoices:
        if invoice.needs_review:
            mark, colour = "review", AMBER
        else:
            mark, colour = "ok", GREEN
        total = f"{invoice.total:,.2f}" if invoice.total is not None else "-"
        print(
            f"  {colour}{mark:<6}{OFF} {invoice.source_file[:40]:<42} "
            f"{(invoice.vendor or 'supplier not read')[:22]:<24} {total:>10} "
            f"{DIM}conf {invoice.confidence:.2f}{OFF}"
        )
        for flag in invoice.flags:
            print(f"         {AMBER}{flag}{OFF}")

    out = Path(args.out)
    xlsx = to_excel(invoices, out / "invoices.xlsx")
    csv_path = to_csv(invoices, out / "invoices.csv")
    items_path = items_to_csv(invoices, out / "line_items.csv")
    report = build_report(invoices, out / "summary.html", folder=short(folder), seconds=seconds)

    review = sum(1 for i in invoices if i.needs_review)
    value = sum(i.total or 0 for i in invoices)
    lines = sum(len(i.line_items) for i in invoices)

    print(f"\n  {BOLD}{len(invoices)} invoices{OFF}, {lines} line items, {value:,.2f} total, read in {seconds:.1f}s")
    print(f"  {len(invoices) - review} went straight through, {AMBER}{review} need a human{OFF}")
    print(f"  excel    {short(xlsx)}")
    print(f"  csv      {short(csv_path)} and {short(items_path)}")
    print(f"  summary  {short(report)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="extractor", description="Turn a folder of invoice PDFs into one spreadsheet.")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="read a folder and write the outputs")
    r.add_argument("--input", "-i", default=str(ROOT / "invoices"), help="folder of PDF files")
    r.add_argument("--out", "-o", default=str(ROOT / "out"), help="where to write the spreadsheet and summary")
    r.set_defaults(func=run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
