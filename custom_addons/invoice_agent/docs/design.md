# invoice_agent — Design Note

**Status:** Draft (binding contract for Weeks 1–2)
**Author:** Hanan
**Date:** 2026-07-18
**Target launch:** 2026-10-10

This note maps the AI invoice pipeline onto Odoo 19's existing accounting models and names the exact
inheritance targets and fields `invoice_agent` will add. It is the reference for all model/field work
until superseded. Companion operational doc: [`../infra/runbook.md`](../infra/runbook.md).

---

## 1. The pipeline

```
scan (PDF/image)
  → OCR (Tesseract)
  → extraction (Claude, structured outputs → JSON header + lines)
  → RAG validation (pgvector + Voyage embeddings → vendor & account matching)
  → draft account.move (move_type = 'in_invoice')
```

Design principle: **extend core accounting in place; do not reimplement it.** The pipeline produces a
*draft vendor bill* that a human posts. Odoo's own invoice lifecycle (`_post`, reconciliation, EDI,
`l10n_*`) is inherited for free by targeting `account.move`.

Relationship to Odoo's built-in OCR: `account.move` already mixes in `account.document.import.mixin`
(see `addons/account/models/account_move.py:74`). That mixin is Odoo's hook for importing a document
into a move (Factur-X/UBL, and the paid IAP "digitization"). `invoice_agent` is a **self-hosted
alternative** to that paid IAP path — Tesseract + Claude instead of IAP — feeding the same
`account.move`. Week 2 decides whether we ride on that mixin's decoder entry points or sit beside them.

---

## 2. Pipeline → model map

| Stage | Model | Reuse / New | Contract |
|---|---|---|---|
| Scan (PDF/image) | `ir.attachment` | **reuse** | Stored as the move's primary attachment via the `mail.thread.main.attachment` mixin. Also linked from the extraction run. |
| OCR text + raw LLM JSON | `invoice.agent.extraction` | **new (1 model)** | Run record: state machine + audit trail. |
| Extracted header | `account.move` (`move_type='in_invoice'`) | **`_inherit`** | Populate `partner_id`, `invoice_date`, `invoice_date_due`, `ref`, `currency_id`. |
| Extracted line items | `account.move.line` (`invoice_line_ids`) | **reuse** | Write product lines; `amount_untaxed/tax/total` compute themselves. |
| Vendor match (RAG) | `res.partner` | **`_inherit`** | Embedding-based match to an existing supplier. |
| Config / routing | `account.journal` | **`_inherit`** | Flag the purchase journal as agent-enabled; hold defaults. |
| Embedding store | — | **OPEN (§6)** | Odoo has no native vector field. |

> Key fact carried from reading core: `invoice_line_ids` is a **subset** of `line_ids`
> (`account_move.py:365`). We write `invoice_line_ids` (product lines); Odoo derives tax/payable lines
> and all totals. We never write `amount_*` directly.

---

## 3. New model — `invoice.agent.extraction`

One record per scan-to-bill run. The only genuinely new model. It is the audit trail and state
machine; it does **not** duplicate any accounting data — it points at the `account.move` it produced.

```python
class InvoiceAgentExtraction(models.Model):
    _name = 'invoice.agent.extraction'
    _description = 'AI Invoice Extraction Run'
    _order = 'create_date desc'
```

| Field | Type | Purpose |
|---|---|---|
| `name` | Char | Human reference (sequence, e.g. `EXTRACT/2026/0001`). |
| `attachment_id` | Many2one `ir.attachment` (required) | The scanned source document. |
| `move_id` | Many2one `account.move` | The draft vendor bill produced (set on success). |
| `partner_id` | Many2one `res.partner` | Matched vendor (from RAG). |
| `journal_id` | Many2one `account.journal` | Target purchase journal. |
| `company_id` | Many2one `res.company` (required) | Multi-company scoping. |
| `state` | Selection | `draft → ocr → extracted → validated → posted / error`. |
| `ocr_text` | Text | Raw Tesseract output. |
| `llm_payload` | Text (JSON) | Claude structured-output response (header + lines), stored verbatim for audit/replay. |
| `model_used` | Char | LLM id, e.g. `claude-opus-4-8`. |
| `confidence` | Float | Overall extraction confidence (0–1). |
| `error_message` | Text | Populated when `state = error`. |

`create_date` / `write_date` / `create_uid` are automatic (audit timestamps).

**Why one JSON blob for lines instead of a child model:** line data lives in `llm_payload` until we
materialize it into real `account.move.line` records on the produced move. Keeps the new-model count at
one, per the design target. Revisit only if per-line review UX demands its own records.

---

## 4. Inheritance targets (extend in place — no `_name`)

Every extension below follows the pattern observed across the ~110 modules that already extend
`account.move`: **(a) new fields, (b) lifecycle override wrapping `super()`, (c) `xpath` view splice.**

### 4.1 `account.move`  (`_inherit = 'account.move'`)
New fields (namespaced `agent_*` to avoid collisions):

| Field | Type | Purpose |
|---|---|---|
| `agent_extraction_id` | Many2one `invoice.agent.extraction` | Back-link to the run that created this bill. |
| `agent_confidence` | Float (related/stored) | Surface extraction confidence on the bill for review. |
| `agent_generated` | Boolean | Flag bills created by the agent (filter/reporting). |

Method: **no core override in v1.** The agent *creates a draft* and stops; the human posts. If we later
need post-time behavior, override `_post` (not `action_post`) so programmatic posting is covered too —
following the `stock_account` pattern (`stock_account/models/account_move.py:29`).

View: `xpath` splice on the vendor bill form to show `agent_confidence` + a link to the extraction run.

### 4.2 `account.move.line`  (`_inherit = 'account.move.line'`)
Optional, thin. Candidate field:

| Field | Type | Purpose |
|---|---|---|
| `agent_line_confidence` | Float | Per-line extraction confidence for review highlighting. |

Kept minimal; totals remain fully core-computed.

### 4.3 `res.partner`  (`_inherit = 'res.partner'`)
Vendor matching for the RAG stage. Fields TBD by §6's embedding decision; at minimum a helper method
`_agent_find_matching_vendor(extracted_vendor)` returning the best `res.partner` by embedding + trigram
fallback.

### 4.4 `account.journal`  (`_inherit = 'account.journal'`)
Config lives on the purchase journal (mirrors how core routes email-to-bill via journal aliases):

| Field | Type | Purpose |
|---|---|---|
| `agent_enabled` | Boolean | This journal accepts agent-generated bills. |
| `agent_default_account_id` | Many2one `account.account` | Fallback expense account when a line can't be matched. |

---

## 5. Security

New model `invoice.agent.extraction` needs `security/ir.model.access.csv`, mirroring core `account`'s
three-tier model (`account/security/ir.model.access.csv:36-38`):

| Group | read | write | create | unlink |
|---|---|---|---|---|
| `account.group_account_invoice` (billing clerk) | 1 | 1 | 1 | 0 |
| `account.group_account_manager` (accountant) | 1 | 1 | 1 | 1 |
| `account.group_account_readonly` (viewer/auditor) | 1 | 0 | 0 | 0 |

No new security *groups* — reuse accounting's. Record rules for multi-company scoping on `company_id`
if/when multi-company is in scope.

---

## 6. Open decisions (resolve in Week 2)

1. **Embedding storage (blocking RAG).** Odoo has no native `vector` field type. Options:
   (a) raw `pgvector` column added to a helper model or to `res.partner` via a `post_init_hook` running
   `CREATE EXTENSION` + `ALTER TABLE`; (b) a dedicated `invoice.agent.vendor.embedding` model with the
   vector column managed by SQL. Leaning (a) to keep the model count at one. **Decision owner: Week 2.**
2. **Ride on `account.document.import.mixin` or sit beside it.** Reusing its decoder entry points gets us
   Odoo's attachment→move plumbing free but couples us to its contract. Prototype both in Week 2.
3. **Field prefix convention.** `agent_*` chosen for readability; confirm no collision with any installed
   `l10n_*`/EDI module before first `-i`.

---

## 7. Module contract (`__manifest__.py` intent)

```python
{
    'name': 'Invoice Agent',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'depends': ['account'],          # account brings account.move, .line, .journal, res.partner ext,
                                     # ir.attachment, and the whole accounting security group set
    'data': [
        'security/ir.model.access.csv',        # security first — always
        'views/invoice_agent_extraction_views.xml',
        'views/account_move_views.xml',        # xpath splices onto the bill form
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
```

`depends = ['account']` is the single most important line: it is the load-graph edge that lets every
`_inherit` above resolve, and pulls in the security groups §5 reuses.

---

## 8. What Week 2 builds first

1. Scaffold the module; `-i invoice_agent` against a scratch DB (proves the manifest + security load).
2. `invoice.agent.extraction` model + views + access CSV (proves the new-model half).
3. `account.move` field additions + `xpath` view splice (proves the extend-in-place half).
4. A stub `action_run_extraction` that creates a draft `in_invoice` from a hard-coded payload
   (proves the pipeline's *last* stage end-to-end before wiring OCR/LLM/RAG upstream).
