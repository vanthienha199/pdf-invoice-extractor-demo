# Invoice PDFs to a spreadsheet (sample project)

One command turns a folder of supplier invoices into a single Excel file, a CSV of invoices, a CSV of line items and an HTML summary. It pulls the supplier, invoice number, date, every line with its quantity and unit price, the net, the tax and the total, then checks its own answers: net plus tax has to equal the total and the line items have to add up to the net. Anything that fails those checks, or has no text layer at all, is flagged for a human instead of being written out as if it were certain.

The 20 sample invoices are generated, not real. They come from six US suppliers in dollars, with combined state and local sales tax, and they use four different supplier layouts, three date formats, two out of state suppliers whose tax is 0.00 rather than missing, one invoice that runs across two pages and one that is a flat scan with no text, because that is what a real inbox looks like.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 tools/make_invoices.py          # write the 20 sample PDFs
python3 -m extractor.cli run            # read them and write out/
python3 -m pytest tests -q              # 13 tests
```

`out/invoices.xlsx` has an Invoices sheet and a Line items sheet, styled for a client rather than dumped: dark header row, frozen panes, filters, dollar formats and banded rows. Anything needing review is tinted amber and sorted to the top, because that is the only part anyone has to act on. `out/summary.html` is a single file you can send on. Point it anywhere with `--input` and `--out`.

## How it decides a row is trustworthy

| Check | Effect |
| --- | --- |
| Supplier, number, date and total all found | raises confidence |
| Net plus tax equals total | raises confidence, a mismatch is flagged with both figures |
| Line items add up to the net | raises confidence, a mismatch names both totals |
| No text layer in the file | confidence zero, flagged as a scan needing OCR |

A trap worth naming, since it is the one that silently corrupts a ledger. A sales tax rate such as `10.30%` has exactly the shape of an amount, so a parser that takes the next number after the word tax records the rate as the tax and every total stops reconciling. Rates are stripped before the amount is read, and a test holds that behaviour in place.

Anything below 0.80, or carrying a flag, lands in the review list in the summary and is tinted in the spreadsheet.

Built by Ha Le as a portfolio sample. Suppliers, amounts and documents are invented. No client data is used anywhere in this repository.
