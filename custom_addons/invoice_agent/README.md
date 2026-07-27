# Invoice Agent

<<<<<<< HEAD
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
=======
AI-powered invoice extraction module for Odoo 19.

## Features

- **AI Extraction Notebook Page**: View raw OCR text, extracted vendor, confidence scores, and per-field extraction details directly on the vendor bill form.
- **AI Agent Queue**: Kanban, list, and search views exposing bills processed by AI. Filter by Low Confidence, Needs Review, or extraction status.
- **Bulk Re-Extraction Wizard**: Select bills in the queue and re-run extraction via the Action menu.
- **Vendor Matching**: Automatic partner matching from extracted JSON payload (VAT → name fallback).
- **Journal Configuration**: Per-journal AI agent toggle, minimum confidence threshold, and auto-post settings.
- **Security Groups**:
  - **Agent Reviewer** (`group_invoice_agent_user`): Can view AI data and review bills. Implies `account.group_account_invoice`.
  - **Agent Manager** (`group_invoice_agent_manager`): Can re-run extraction, approve/reject, and configure journals. Implies Agent Reviewer.
- **Multi-Company**: Record rules restrict extraction lines to the user's companies.

## Installation

1. Place `invoice_agent` in your addons path (e.g., `custom_addons/`).
2. Restart Odoo and update module list.
3. Install **Invoice Agent**.
4. Assign users to **Invoicing > Invoice Agent > Agent Reviewer** (or **Agent Manager**).
5. Enable AI extraction on individual journals: **Accounting > Configuration > Journals > [select journal] > AI Agent tab**.

## Queue Access

Navigate to **Invoicing > AI Agent Queue**. The queue shows bills with `ai_extraction_status` in `extracted`, `validated`, or `failed`. By default the "Needs Review" filter is active.

## Bulk Re-Extraction

1. Open the AI Agent Queue (list or kanban view).
2. Select one or more bills.
3. Click **Action > Re-Run AI Extraction**.
4. Confirm in the wizard. All selected bills are reset to `pending`; extraction lines are deleted.

## Form View

The **AI Extraction** notebook page appears on vendor bills (`in_invoice`, `in_refund`). It shows:
- Extraction status (badge with color coding)
- Confidence scores (progress bars)
- OCR text
- Extracted JSON payload
- Per-field extraction lines
- Variance analysis (extracted total vs system total)

## Architecture

```
invoice_agent/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── account_move.py          # AI fields + vendor matching + computed variances
│   ├── account_move_line.py     # ai_confidence on invoice lines
│   ├── account_journal.py       # ai_agent_enabled, ai_min_confidence, ai_auto_post
│   ├── res_partner.py           # AI stats (invoice count, avg confidence)
│   └── invoice_agent_extraction_line.py  # Per-field extraction results
├── security/
│   ├── invoice_agent_groups.xml  # group_invoice_agent_user + group_invoice_agent_manager
│   ├── invoice_agent_rules.xml   # Multi-company record rule
│   └── ir.model.access.csv       # ACLs for both groups
├── views/
│   ├── account_move_views.xml    # Form inheritance (AI Extraction notebook page)
│   ├── account_journal_views.xml # AI Agent tab on journal form
│   ├── res_partner_views.xml     # AI Invoicing tab on partner form
│   └── invoice_agent_views.xml   # Queue kanban/list/search + action + menu + wizard binding
├── wizard/
│   ├── __init__.py
│   ├── bulk_process_wizard.py    # TransientModel for bulk re-extraction
│   └── bulk_process_wizard_views.xml
└── tests/
    ├── __init__.py
    └── test_bulk_wizard.py
```

## Development

Run tests:
```bash
odoo-bin -c odoo.conf -d dev --test-tags /invoice_agent --stop-after-init
```

Update module after changes:
```bash
odoo-bin -c odoo.conf -d dev -u invoice_agent --stop-after-init
>>>>>>> docs/posting-flow
