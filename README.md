# Invoice PDFs to a spreadsheet (sample project)

One command turns a folder of supplier invoices into a single Excel file, a CSV of invoices, a CSV of line items and an HTML summary. It pulls the supplier, invoice number, date, every line with its quantity and unit price, the net, the tax and the total, then checks its own answers: net plus tax has to equal the total and the line items have to add up to the net. Anything that fails those checks, or has no text layer at all, is flagged for a human instead of being written out as if it were certain.

The 20 sample invoices are generated, not real. They use four different supplier layouts, three date formats, a zero rated supplier, one invoice that runs across two pages and one that is a flat scan with no text, because that is what a real inbox looks like.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 tools/make_invoices.py          # write the 20 sample PDFs
python3 -m extractor.cli run            # read them and write out/
python3 -m pytest tests -q              # 11 tests
```

`out/invoices.xlsx` has an Invoices sheet and a Line items sheet, with anything needing review tinted amber. `out/summary.html` is a single file you can send to a client. Point it anywhere with `--input` and `--out`.

## How it decides a row is trustworthy

| Check | Effect |
| --- | --- |
| Supplier, number, date and total all found | raises confidence |
| Net plus tax equals total | raises confidence, a mismatch is flagged with both figures |
| Line items add up to the net | raises confidence, a mismatch names both totals |
| No text layer in the file | confidence zero, flagged as a scan needing OCR |

Anything below 0.80, or carrying a flag, lands in the review list in the summary and is tinted in the spreadsheet.

Built by Ha Le as a portfolio sample. Suppliers, amounts and documents are invented. No client data is used anywhere in this repository.
