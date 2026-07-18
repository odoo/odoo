# Invoice Agent

An Odoo 19 addon that turns a scanned supplier invoice into a draft `account.move`.

Pipeline: scan → OCR (Tesseract) → extraction (Claude, structured outputs) → RAG validation
(pgvector + Voyage embeddings) → draft vendor bill.

It **extends core accounting** (`account.move`, `account.move.line`, `account.journal`,
`res.partner`) rather than reimplementing it.

## Layout

| Path | What |
|---|---|
| `infra/runbook.md` | Operational record of the AWS environment. Append-only. |

## Deployment

Docker on AWS EC2 (`me-south-1`), deployed by GitHub Actions. See `infra/runbook.md` for the
live environment's instance ID, Elastic IP, and the SSH command that works.
