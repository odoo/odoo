# l10n_cn_edi_baiwang — Master Implementation Plan

> **Last Updated:** 2026-06-10
> **Status:** MVP in development. Only tax category code lookup is confirmed working from Odoo UI.

---

## Document Directory

| File | Purpose |
|------|---------|
| `PLAN.md` (this file) | Master architecture, decisions, status, and roadmap |
| `API_REFERENCE.md` | Baiwang API contracts: endpoints, payloads, signing, patterns (validated against sandbox) |
| `baiwang_test.py` | Standalone reference script that validated ALL Baiwang APIs against sandbox (working) |

---

## 1. Architecture: Odoo IAP Proxy

**Decision:** The module uses an IAP Proxy architecture. Direct Baiwang calls from the Odoo tenant are not viable for SaaS deployment.

### Why IAP (not direct calls)

- **Security:** No Baiwang passwords, salts, or App Secrets live on the Odoo tenant database.
- **GFW Bypass:** `*.odoo.com` domains face throttling in China. The proxy URL is configurable via `ir.config_parameter`, allowing immediate switching to `iap.cn.odoo.com` without code changes.
- **Tenant Isolation:** Each Odoo database is mapped to a specific `iap.account` on the IAP server.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│ Odoo Tenant (Client)                                                │
│  - Builds raw business payload (invoice lines, buyer info, etc.)    │
│  - Sends to IAP via iap_jsonrpc with org_auth_code + tax_no        │
│  - Zero knowledge of Baiwang signing/tokens/secrets                 │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ iap_jsonrpc
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ IAP Proxy Server                                                    │
│  - Validates iap.account identity                                   │
│  - Looks up Baiwang credentials for tenant's org_auth_code          │
│  - Wraps payload into correct Baiwang pattern (v6.0 nested/v7.0 flat)│
│  - Signs request (MD5), manages OAuth tokens, handles retry         │
│  - Forwards to Baiwang and returns response                         │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ HTTPS POST
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Baiwang Open API                                                    │
│  sandbox-openapi.baiwang.com (test)                                 │
│  openapi.baiwang.com (prod)                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Rate Limiting & Queueing (IAP Proxy)

- **Global Limit:** Baiwang enforces a hard limit of **20 requests/second** shared across *all* Odoo users globally under our single AppKey (approx. 1.728M requests/day).
- **Queue Strategy:** To prevent throttling, outbound requests (especially batch operations) must be placed in a standard Odoo queue/cron system rather than fired synchronously.
- **No Dynamic Limits:** We will *not* implement dynamic per-database rate limiting on the IAP proxy to avoid edge-case disasters. We rely on a reasonable global queue rate. If we hit the ceiling due to user growth, we will apply for a higher AppKey limit directly with Baiwang.

### Dynamic Routing (China Tunnel)

```python
endpoint = self.env['ir.config_parameter'].sudo().get_param(
    'l10n_cn_baiwang.iap_endpoint',
    default='https://iap.odoo.com/api/baiwang/v1'
)
```

### Current State (Prototype)

The current codebase (`baiwang_client.py`) implements **direct calls** to Baiwang, storing all credentials on `res.company`. This served as a validation tool to confirm the API contracts work. It needs to be refactored into:
- **IAP Server Side:** Token management, signing logic, credential storage → moves to the IAP server
- **Odoo Client Side:** Thin `iap_jsonrpc` caller that sends business payloads only

---

## 2. Configuration (res.company — Target State)

### Target (IAP Architecture)

| Field | Type | Storage | Purpose |
|-------|------|---------|---------|
| `l10n_cn_edi_mode` | Selection | store=True | `test` / `prod` |
| `l10n_cn_baiwang_org_auth_code` | Char | store=True | Permanent orgAuthCode identifying the enterprise |
| `l10n_cn_baiwang_subscription_status` | Selection | store=True | `not_subscribed` / `subscribed` / `authorized` — tracks registration flow |

> **Tax ID:** Read from native `res.company.vat` — no duplicate column.

### Current Prototype (Direct Calls — to be removed)

These fields exist in code but will be eliminated once IAP is ready:

| Field | Purpose | Fate |
|-------|---------|------|
| `l10n_cn_baiwang_app_key` | App Key | → IAP server |
| `l10n_cn_baiwang_app_secret` | App Secret | → IAP server |
| `l10n_cn_baiwang_username` | Username | → IAP server |
| `l10n_cn_baiwang_password` | Password | → IAP server |
| `l10n_cn_baiwang_salt` | Salt | → IAP server |
| `l10n_cn_baiwang_cached_token` | Cached OAuth token | → IAP server |
| `l10n_cn_baiwang_refresh_token` | Refresh token | → IAP server |
| `l10n_cn_baiwang_token_expiry` | Token expiry | → IAP server |

---

## 3. Tax Category Codes (税收分类编码)

**Decision:** Use a dedicated model loaded from a 5,555-line CSV. No runtime API calls to Baiwang for code lookup.

### Pattern (follows `product_unspsc` module)

- **Model:** `l10n_cn.tax.category.code`
- **Fields:** `code` (Char, 19-digit), `name` (Char, Chinese name)
- **Loaded via:** `post_init_hook` using fast `COPY` SQL (sub-3s load time)
- **Product field:** `l10n_cn_tax_category_code_id` = Many2one on `product.template`
- **Autocomplete:** `_rec_names_search = ['name', 'code']` for user-friendly lookup
- **CSV:** `data/product_tax_category_code.csv` (already exists, 5,555 rows, `code,name` format)

### Migration from Current State

- Current: `l10n_cn_tax_category_code` is a Char field on `product.template`
- Current: `action_fetch_baiwang_tax_code()` calls `baiwang.bizinfo.search` API
- Target: Replace with Many2one to the new model; remove the API call action

---

## 4. Account Move (Invoice/Credit Note) Fields

Fields on `account.move` for Baiwang e-Fapiao tracking:

| Field | Type | Purpose |
|-------|------|---------|
| `l10n_cn_baiwang_state` | Selection | `not_sent` / `sent` / `issued` / `failed` |
| `l10n_cn_baiwang_invoice_type_code` | Selection | `01` (Digital Special 全电专票) / `02` (Digital General 全电普票) |
| `l10n_cn_baiwang_invoice_no` | Char | Issued fapiao number (20 digits for 全电) |
| `l10n_cn_baiwang_invoice_date` | Char | Fapiao date (YYYYMMDDHHmmss format from Baiwang) |
| `l10n_cn_baiwang_serial_no` | Char | Unique request serial for idempotency |
| `l10n_cn_baiwang_qr_code` | Char | Invoice QR code string |
| `l10n_cn_baiwang_error_message` | Text | Last error message |
| `l10n_cn_baiwang_red_form_type` | Selection | Red form reason code |
| `l10n_cn_baiwang_original_invoice_id` | Many2one | Link to original blue invoice being reversed |
| `l10n_cn_edi_document_ids` | One2many | Link to EDI tracking documents |

### Invoice Type Codes (sandbox-validated)

Only **fully-digital (全电)** types are supported — no physical tax hardware needed:

| Code | Type | Notes |
|------|------|-------|
| `01` | 全电专用发票 (Digital Special) | ✅ Works without terminal |
| `02` | 全电普通发票 (Digital General) | ✅ Works without terminal |

> Codes `004`, `007`, `026`, `028` require physical tax control hardware — not supported.

### Red Form Reason Codes (redInvoiceLabel)

| Code | Chinese | English | Baiwang Field |
|------|---------|---------|---------------|
| `01` | 开票有误 | Billing Error | `redInvoiceLabel: "01"` |
| `02` | 销货退回 | Sales Return | `redInvoiceLabel: "02"` |
| `03` | 服务中止 | Service Termination | `redInvoiceLabel: "03"` |
| `04` | 销售折让 | Sales Discount | `redInvoiceLabel: "04"` |

---

## 5. EDI Document Model (l10n_cn_edi.document)

Dedicated model for tracking red form lifecycle (separate from `account.move` to avoid column bloat):

| Field | Type | Purpose |
|-------|------|---------|
| `move_id` | Many2one → account.move | Parent credit note |
| `state` | Selection | `draft` / `red_form_pending` / `red_form_confirmed` / `failed` |
| `baiwang_uuid` | Char | Red form UUID from Baiwang |
| `baiwang_red_form_number` | Char | Red Confirmation No (红字确认单号) |
| `baiwang_confirm_state` | Char | Baiwang confirmState code |
| `baiwang_red_invoice_no` | Char | Issued red invoice number |
| `error_message` | Text | Error details |

### Confirm State Mapping

| Code | Meaning | EDI Doc State |
|------|---------|---------------|
| `01` | Auto-approved (no confirmation needed) | `red_form_confirmed` |
| `02` | Waiting for buyer to confirm | `red_form_pending` |
| `03` | Waiting for seller to confirm | `red_form_pending` |
| `04` | Both parties confirmed | `red_form_confirmed` |
| `05`-`10` | Rejected/cancelled/expired/revoked | `failed` |

---

## 6. Execution Flows

### 6.1 Blue Invoice Issuance (out_invoice)

1. User posts a Customer Invoice (country = CN)
2. User triggers **Send & Print** → "Issue E-Fapiao (Baiwang)" checkbox is auto-checked
3. `account.move.send` hook calls `_l10n_cn_baiwang_issue_invoice()`
4. Odoo builds payload: `invoiceTypeCode`, buyer info, line items (with tax category codes)
5. Payload sent to IAP proxy → proxy wraps in v6.0 `{taxNo, data:{...}}` format → signs → sends to Baiwang
6. On success: `l10n_cn_baiwang_state = 'issued'`, stores `invoiceNo`, `invoiceDate`, `invoiceQrCode`
7. On failure: `l10n_cn_baiwang_state = 'failed'`, stores error message

### 6.2 Red Form / Credit Note (out_refund) — Outgoing

**Control Flow: Blocking Confirm Until Red Form is Processed**

When a Credit Note is linked to an original invoice (`reversed_entry_id`) that already has a Baiwang fapiao number (`l10n_cn_baiwang_invoice_no`), the standard "Confirm" (Post) button is **hidden/disabled**. The user is forced to first submit the red form to Baiwang. Only after the red form is confirmed does the Confirm button become available again.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Credit Note (Draft)                                                       │
│                                                                           │
│  Original Invoice has Fapiao No? ─── NO ──→ Normal flow (Confirm visible)│
│              │                                                            │
│             YES                                                           │
│              │                                                            │
│              ▼                                                            │
│  Hide "Confirm" button                                                    │
│  Show "Send Red Form" button (primary CTA)                                │
│              │                                                            │
│              ▼ (user clicks)                                              │
│  Call redinvoice.add via IAP                                              │
│              │                                                            │
│              ├── confirmState == '01' (auto-approved)                      │
│              │       → Show "Red Form Confirmed" ribbon                   │
│              │       → Re-enable "Confirm" button                         │
│              │                                                            │
│              └── confirmState == '02'/'03' (pending)                       │
│                      → Show "Red Form Requested" ribbon (info blue)       │
│                      → Keep "Confirm" disabled                            │
│                      → Cron polls for status update                       │
│                              │                                            │
│                              ▼ (confirmed by counterpart)                 │
│                      → Update ribbon to "Red Form Confirmed"              │
│                      → Re-enable "Confirm" button                         │
└──────────────────────────────────────────────────────────────────────────┘
```

**Ribbon states** (following `l10n_my_edi` pattern with `widget="web_ribbon"`):
- `"Red Form Requested"` — `text-bg-info` (blue) — waiting for confirmation
- `"Red Form Confirmed"` — (no ribbon, normal state, Confirm button available)
- `"Red Form Rejected"` — `text-bg-warning` (yellow) — requires user action

**Step 1: Submit Red Form**
1. User creates Credit Note (via reversal wizard with reason code, or manually)
2. `l10n_cn_baiwang_red_form_type` is set (mandatory before submission)
3. "Confirm" button is hidden because original invoice has a fapiao number
4. User clicks **"Send Red Form"** button (primary, highlighted)
5. Odoo builds red confirmation payload referencing original blue invoice
6. Payload sent via IAP → proxy uses v7.0 flat body → `redinvoice.add`
7. Response:
   - `confirmState == '01'` → auto-approved → ribbon cleared → Confirm button re-enabled
   - `confirmState == '02'/'03'` → pending → "Red Form Requested" ribbon shown

**Step 2: Poll for Confirmation (Cron)**
- **Hourly cron** (for outgoing red forms): `_cron_check_red_form_status()`
- Queries all EDI documents where `state == 'red_form_pending'`
- Calls `redinvoice.redforminfo` (v6.0 flat) per UUID
- Updates state based on `confirmState` response
- When confirmed: clears ribbon, re-enables Confirm on the credit note

**Step 3: Revoke (optional)**
- If seller wants to cancel: calls `redinvoice.operate` with `confirmType: '03'`

### 6.3 Vendor Red Forms (Incoming)

**Daily Cron: Discover Incoming Red Forms**

The `redinvoice.formlist` API can only be polled once per day. A dedicated daily cron handles discovery:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Daily Cron: _cron_poll_incoming_red_forms()                             │
│                                                                         │
│  1. Call redinvoice.formlist (buySelSelector="1", as buyer)              │
│     → Returns list of red forms sent TO us by vendors                   │
│                                                                         │
│  2. For each red form in results:                                       │
│     a. Call redinvoice.redforminfo (get full details + line items)       │
│     b. Try to match originalInvoiceNo against existing account.move      │
│        records where l10n_cn_baiwang_invoice_no matches                  │
│     c. If matched: link the red form to that move                        │
│     d. Create l10n_cn_edi.document record with incoming details          │
│                                                                         │
│  3. For red forms needing confirmation (confirmState == '03'):           │
│     → Create mail.activity (To-Do) on the matched move                  │
│     → Activity prompts user to Confirm or Reject                        │
│                                                                         │
│  4. For red forms already auto-confirmed (confirmState == '01'):         │
│     → Log note on matched move                                          │
│     → If auto_create_vendor_cn setting enabled: create in_refund         │
└────────────────────────────────────────────────────────────────────────┘
```

**Vendor Red Form Action UI (Banner Pattern)**

When an incoming red form requires confirmation, the user sees a notification banner on the matched invoice (or in an activity view):

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⚠️  Red Form XXXX-XXXX received from [Vendor Name]                    │
│     Credit amount (tax excl.): ¥ X,XXX.XX                             │
│     Credit tax: ¥ XXX.XX                                              │
│                                                                       │
│                                    [01 - Confirm]    [02 - Reject]    │
└──────────────────────────────────────────────────────────────────────┘
```

**Implementation approach:**
- Use `mail.activity` with a custom activity type (`l10n_cn_baiwang_red_form_action`) to notify the responsible user
- The activity summary contains the red form number and amounts
- Action buttons call `redinvoice.operate` with `confirmType: "01"` (confirm) or `"02"` (reject)
- On confirm: optionally auto-create `in_refund` (vendor credit note) linked to the original vendor bill
- On reject: mark EDI doc as `failed`, dismiss activity

**Matching Logic:**
- Match `originalInvoiceNo` from the red form against `l10n_cn_baiwang_invoice_no` on existing `account.move` records
- If matched → link via the EDI document model
- If not matched → still create the activity but attach to the company's default journal instead (manual resolution needed)

Note: Advanced inbound compliance APIs (e.g., baiwang.input.compliance.validate, VAT deduction) are explicitly out of scope for Phase 1. We only process basic Draft Vendor Bills and Incoming Red Forms.
---

## 7. Integration Points

### Send & Print Wizard (`account.move.send`)
- Registers `cn_baiwang` as an extra EDI option
- Only applicable when: country=CN, move_type=out_invoice, state=posted, credentials configured
- Hooks into `_call_web_service_before_invoice_pdf_render`

### Credit Note Reversal Wizard (`account.move.reversal`)
- Adds `l10n_cn_baiwang_red_form_type` **selection field** (new localized field, NOT overriding the native `reason` Char)
- Since we cannot change `reason`'s field type from Char to Selection, we:
  - Add a new field: `l10n_cn_baiwang_red_form_type` (Selection)
  - In the view: **replace** the `reason` field with our selection field for CN companies (using `invisible` conditions on country_code)
  - Values:
    - `01` — Invoice error (开票有误)
    - `02` — Sales return (销货退回)
    - `03` — Service termination (服务中止)
    - `04` — Sales allowance (销售折让)
  - `@api.onchange`: when selection changes, auto-fill the native `reason` text field with the English label
- Propagates to the created credit note's `l10n_cn_baiwang_red_form_type` via `_prepare_default_reversal`

### Scheduled Actions (ir.cron)

| Cron | Frequency | Purpose |
|------|-----------|---------|
| "Baiwang: Check Outgoing Red Form Status" | Hourly | Poll `redforminfo` for pending outgoing red forms |
| "Baiwang: Poll Incoming Red Forms" | Daily | Call `formlist` (buyer role) to discover incoming vendor red forms |

### Account Move Form View (UI Layout)

**New "Baiwang E-Fapiao" tab** in the invoice notebook (following `l10n_my_edi` pattern):
- Move all Baiwang-specific fields OUT of the main form into a dedicated tab
- Tab visible when: `country_code == 'CN'` and `move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')`
- Contents:
  - `l10n_cn_baiwang_state` (status badge)
  - `l10n_cn_baiwang_invoice_type_code` (fapiao type)
  - `l10n_cn_baiwang_invoice_no` (fapiao number — moved from under "Customer")
  - `l10n_cn_baiwang_invoice_date`
  - `l10n_cn_baiwang_qr_code`
  - `l10n_cn_baiwang_serial_no`
  - `l10n_cn_baiwang_error_message` (if failed)
  - `l10n_cn_baiwang_red_form_type` (for credit notes)
  - `l10n_cn_baiwang_original_invoice_id` (for credit notes)

**Ribbons** (positioned before existing `web_ribbon`, same as MY EDI):
- `"Red Form Requested"` — `text-bg-info` — when `l10n_cn_baiwang_state == 'sent'` and move_type is `out_refund`
- `"Red Form Rejected"` — `text-bg-warning` — when `l10n_cn_baiwang_state == 'failed'` and move_type is `out_refund`

**Header Buttons:**
- `"Send Red Form"` — primary, visible on `out_refund` when:
  - `state == 'draft'`
  - Original invoice has fapiao number
  - `l10n_cn_baiwang_state` not in (`sent`, `issued`)
- Standard "Confirm" button: hidden/disabled when red form is required but not yet confirmed

---

## 8. EDI Architecture Alignment & Client Interface

### 8.1 Pattern: Modern Odoo EDI (NOT `account.edi.format`)

**Finding:** The old `account.edi.format` model is a **legacy pattern** from Odoo 15-16 era, used in the `iap-odoo` repo (India `l10n_in_edi`, Mexico). The modern approach (master branch, 17+) used by `l10n_my_edi` does NOT inherit `account.edi.format` at all.

**Our module follows the modern pattern:**

| Component | l10n_my_edi (reference) | l10n_cn_edi_baiwang (ours) |
|-----------|------------------------|----------------------------|
| EDI Document Model | `myinvois.document` (own model, own states) | `l10n_cn_edi.document` (own model, own states) |
| Send hook | `account.move.send._get_all_extra_edis()` | Same — registers `cn_baiwang` |
| Web service call | `_call_web_service_before_invoice_pdf_render()` | Same |
| Async polling | Hourly cron on document model | Same (hourly for outgoing status) |
| IAP proxy | `l10n_my_edi_proxy` in `iap-apps/iap_services/` | `l10n_cn_edi_baiwang_proxy` (to build) |
| State on move | Computed from document model | Same pattern |
| Ribbon/status | `web_ribbon` (Processing / Rejected) | Same (Red Form Requested / Rejected) |

**Key code references:**
- `odoo/addons/l10n_my_edi/models/account_move_send.py` — minimal, just provides extra attachments
- `odoo/addons/l10n_my_edi/models/account_move.py` — `action_l10n_my_edi_send_invoice()` creates document then calls `action_submit_to_myinvois()`
- `odoo/addons/l10n_my_edi/models/myinvois_document.py:1354` — `_myinvois_statuses_update_cron()` runs hourly
- `odoo/addons/l10n_my_edi/data/ir_cron.xml` — `interval_number=1, interval_type=hours`
- `iap-apps/iap_services/l10n_my_edi_proxy/controllers/controllers.py` — IAP proxy routes

**Why not `account.edi.format`:**
- No `_check_format_error` or `_needs_web_services` — those are legacy concepts
- Modern modules use `account.move.send` extra EDIs for the submission trigger
- Async polling is just a cron on the document model, not tied to any format class
- The old pattern required `account_edi` module as dependency; new pattern only needs `account`

### 8.2 IAP Proxy Structure (Target)

Based on `l10n_my_edi_proxy`, our proxy should expose these routes:

```python
# iap-apps/iap_services/l10n_cn_edi_baiwang_proxy/controllers/controllers.py

class L10nCnEdiBaiwangControllers(http.Controller):

    @route('/api/l10n_cn_edi_baiwang/1/issue_invoice', type='json', auth='public', save_session=False)
    @authenticate_request
    def issue_invoice(self, payload, user, **kw):
        """Issue blue invoice via Baiwang. Handles token, signing, v6.0 wrapping."""
        ...

    @route('/api/l10n_cn_edi_baiwang/1/submit_red_form', type='json', auth='public', save_session=False)
    @authenticate_request
    def submit_red_form(self, payload, user, **kw):
        """Submit red letter confirmation. Handles token, signing, v7.0 flat body."""
        ...

    @route('/api/l10n_cn_edi_baiwang/1/query_red_form', type='json', auth='public', save_session=False)
    @authenticate_request
    def query_red_form(self, red_confirm_uuid, user, **kw):
        """Get red form detail (v6.0 flat)."""
        ...

    @route('/api/l10n_cn_edi_baiwang/1/poll_red_form_list', type='json', auth='public', save_session=False)
    @authenticate_request
    def poll_red_form_list(self, filters, user, **kw):
        """Poll incoming red forms (daily, buyer role)."""
        ...

    @route('/api/l10n_cn_edi_baiwang/1/operate_red_form', type='json', auth='public', save_session=False)
    @authenticate_request
    def operate_red_form(self, red_confirm_uuid, red_confirm_no, confirm_type, user, **kw):
        """Confirm/reject/revoke a red form."""
        ...
```

### 8.3 Odoo Client (Thin IAP Caller)

```python
# models/baiwang_client.py (target state)
from odoo import models
from odoo.exceptions import UserError
from odoo.addons.iap.tools import iap_tools

class BaiwangIapClient(models.AbstractModel):
    _name = 'l10n_cn_edi_baiwang.client'
    _description = 'Baiwang IAP Client'

    def _call_iap_proxy(self, route, payload, company):
        endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cn_baiwang.iap_endpoint',
            default='https://iap.odoo.com'
        )
        url = f'{endpoint}/api/l10n_cn_edi_baiwang/1/{route}'

        params = {
            'org_auth_code': company.l10n_cn_baiwang_org_auth_code,
            'tax_no': company.vat,
            'payload': payload,
            'environment': company.l10n_cn_edi_mode or 'test',
        }

        response = iap_tools.iap_jsonrpc(url, params=params, timeout=20)
        if not response.get('success'):
            raise UserError(f"Baiwang EDI Error: {response.get('error_message')}")
        return response.get('response', {})

    def issue_blue_invoice(self, company, move_data):
        return self._call_iap_proxy('issue_invoice', move_data, company)

    def submit_red_form(self, company, flat_red_data):
        return self._call_iap_proxy('submit_red_form', flat_red_data, company)

    def query_red_form_detail(self, company, red_confirm_uuid):
        return self._call_iap_proxy('query_red_form', {'red_confirm_uuid': red_confirm_uuid}, company)

    def query_red_form_list(self, company, filters=None):
        return self._call_iap_proxy('poll_red_form_list', {'filters': filters or {}}, company)

    def operate_red_form(self, company, red_confirm_uuid, red_confirm_no, confirm_type):
        return self._call_iap_proxy('operate_red_form', {
            'red_confirm_uuid': red_confirm_uuid,
            'red_confirm_no': red_confirm_no,
            'confirm_type': confirm_type,
        }, company)
```

---

## 9. API Business Rules & UX Notes

### 9.1 `autoIssueSwitch` = Always `"Y"`

When calling the Red Form Issue API (`redinvoice.add`), always send `autoIssueSwitch: "Y"`. This means the red invoice is automatically issued upon confirmation — no separate step needed.

### 9.2 Invoice Date vs Fapiao Date Warning

After a blue invoice is successfully issued (fapiao number returned), compare Odoo's `invoice_date` with the Baiwang `invoiceDate` (stored in `l10n_cn_baiwang_invoice_date`). If they differ, show a **non-blocking warning** message:

> "Invoice Date is different from Fapiao Date. Please be aware of the consistency between E-fapiao Date and Odoo Invoice Date."

**Implementation:** This should be a computed field or onchange-triggered banner (similar to `_check_balanced` warnings) that appears on the invoice form when the two dates don't match. The fapiao date is in `YYYYMMDDHHmmss` format — compare only the date part (`YYYYMMDD`) against `invoice_date`.

---

## 10. Known Issues & Investigation Items

### 10.1 Auth Endpoint Signing Discrepancy ⚠️

**Status:** Needs re-testing.

| | `baiwang_test.py` (working) | `baiwang_client.py` (Odoo) |
|---|---|---|
| Signing | NOT signed | Signed with `signType: SHA256` |
| Body format | `requests.post(json=body)` | Compact JSON via `data=` |
| Additional URL params | None | `signType`, `encryptType`, `encryptScope` |

The `API_REFERENCE.md` explicitly states "No signature required" for `baiwang.oauth.token`. The Odoo code adds signing — this may cause token fetch failures.

**Action:** Before IAP refactor, verify whether the auth endpoint sign/no-sign behavior matters. The test script works without it.

### 10.2 Invoice Issue Not Yet Verified from Odoo

The blue invoice flow (`baiwang.output.invoice.issue`) works in `baiwang_test.py` but has not been verified end-to-end from the Odoo UI. The auth discrepancy (9.1) likely blocks this.

### 10.3 Red Invoice Flow Not Yet Verified

All red invoice APIs (`redinvoice.add`, `redinvoice.operate`, `redinvoice.formlist`, `redinvoice.redforminfo`) were validated in the test script but not from Odoo.

---

## 11. Baiwang User Registration & orgAuthCode Callback

### Overview (Sequence)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ Odoo Settings → China Electronic Invoicing (Baiwang)                          │
│                                                                               │
│  Step 1: [Subscribe to Baiwang]  (button)                                     │
│           │                                                                   │
│           └──→ Opens new tab to Baiwang affiliate/channel order URL            │
│               (① baiwang.saas.ordercenter.createChannelOrder)                  │
│               User pays & registers account on Baiwang portal                 │
│               Baiwang calls our callback → we know order succeeded             │
│                                                                               │
│  Step 2: [Authorize Odoo to use Baiwang]  (button, shown after Step 1)        │
│           │                                                                   │
│           └──→ Odoo calls ② baiwang.usercenter.org.addOpenOrgRelApi            │
│               → Baiwang sends authorization email to customer                  │
│               → Customer clicks "Authorize" in the email                       │
│               → Baiwang calls our callback with orgAuthCode                    │
│               (③ baiwang.openplatform.isv.getAuthCode)                         │
│                                                                               │
│  Result: orgAuthCode is stored on res.company → ready to issue invoices       │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Callback Controller(s)

Baiwang callbacks are hosted on the **IAP proxy side**, not on each Odoo database.

1. **Order completion callback** — Baiwang confirms the customer has paid/registered
2. **Authorization callback** — Baiwang returns the `orgAuthCode` after customer authorizes

This matches API reference §10: a single callback URL per environment (dev/stg/prod), managed by IAP.

```python
# iap-apps/iap_services/l10n_cn_edi_baiwang_proxy/controllers/controllers.py

@route('/l10n_cn_edi_baiwang/callback/order_complete',
       type='http', auth='public', methods=['GET', 'POST'], csrf=False)
def callback_order_complete(self, **kw):
    """Baiwang -> IAP: mark tenant as subscribed."""
    ...

@route('/l10n_cn_edi_baiwang/callback/org_auth_code',
       type='http', auth='public', methods=['GET', 'POST'], csrf=False)
def callback_org_auth_code(self, **kw):
    """Baiwang -> IAP: store orgAuthCode for tenant taxNo."""
    ...

@route('/api/l10n_cn_edi_baiwang/1/get_registration_state',
       type='json', auth='public', save_session=False)
def get_registration_state(self, tax_no, **kw):
    """Odoo -> IAP: read current subscription status + orgAuthCode."""
    ...
```

Odoo **does not expose public callback routes** for this flow anymore.

### Odoo Sync Flow

After Baiwang calls IAP, Odoo users click **"Sync Registration Status"** in settings.
Odoo calls IAP endpoint `get_registration_state` and updates:
- `l10n_cn_baiwang_subscription_status`
- `l10n_cn_baiwang_org_auth_code`

This avoids exposing per-database public callbacks while still allowing user-driven refresh.

### Settings UI (res.config.settings)

New field on `res.company` to track the registration state:

| Field | Type | Values |
|-------|------|--------|
| `l10n_cn_baiwang_subscription_status` | Selection | `not_subscribed` / `subscribed` / `authorized` |

**Button visibility logic:**

| State | "Subscribe to Baiwang" button | "Authorize Odoo" button | "Sync Registration Status" button | Status label |
|-------|------------------------------|-------------------------|-------------------------------|--------------|
| `not_subscribed` | ✅ Visible (primary) | Hidden | ✅ Visible | — |
| `subscribed` | Hidden | ✅ Visible (primary) | ✅ Visible | "Subscribed, awaiting authorization" |
| `authorized` | Hidden | Hidden | ✅ Visible | "✓ Connected" + orgAuthCode displayed |

### Action: "Authorize Odoo to use Baiwang"

When the user clicks this button:
1. Odoo redirects the user to the Baiwang authorization link
2. Baiwang sends an authorization invitation email to the customer
3. Customer clicks authorize in the email
4. Baiwang calls **IAP** callback with `orgAuthCode`
5. User clicks **Sync Registration Status** in Odoo to pull the updated state from IAP

### Manual Fallback

Users can still paste the `orgAuthCode` manually in settings during development (test orgAuthCode available) or if callback sync fails.

### Future Hardening
- IP whitelist on IAP callback routes once Baiwang provides server IPs
- Optional HMAC signature verification if Baiwang supports it
- Logging/audit trail for orgAuthCode changes on IAP side
- Service renewal reminders (Baiwang sends expiry notifications)

---

## 12. POS Integration (Future — Beyond Phase 3)

The EDI Document abstraction enables POS without rewriting the Baiwang engine:

1. Customer finishes meal → Receipt prints QR Code
2. Customer scans QR → Opens Odoo web form (collects Company Name, TIN, Email)
3. Submit → Odoo merges POS order lines + form data → Creates EDI Document
4. Existing Baiwang engine processes it identically to back-office invoices

---

## 13. Task Breakdown & Priority Queue

Implementation order for this task. Not "phases" — these are prioritized work items within a single task.

| # | Work Item | Status | Notes |
|---|-----------|--------|-------|
| **WI-0** | Direct-call prototype, tax category CSV (Many2one model), API validation | ✅ Done | Test script validates all APIs |
| **WI-1** | Registration flow with callbacks hosted on IAP (`order_complete`, `org_auth_code`) + Odoo sync action | ✅ | IAP callback module added and Odoo settings wired to sync |
| **WI-2** | IAP proxy build + refactor client to thin `iap_jsonrpc` | 🔲 | Core infra |
| **WI-3** | Blue invoice E2E (Send & Print → IAP → Baiwang → fapiao number stored) | 🔲 | Main business value |
| **WI-4** | Baiwang E-Fapiao tab UI, date warning banner, ribbons | 🟡 In progress | Date warning + ribbons implemented; finalize layout polishing |
| **WI-5** | Credit note wizard (red form type selection replacing reason field) | 🔲 | |
| **WI-6** | Outgoing red form E2E (blocking Confirm, redinvoice.add, hourly cron) | 🟡 In progress | Draft-stage send + Confirm blocking implemented; end-to-end verification pending |
| **WI-7** | Incoming vendor red forms (daily formlist poll, activity, confirm/reject) | 🔲 | |

### Project-Level Phases (Separate Tasks, Different Scope)

| Phase | Scope | Owner |
|-------|-------|-------|
| **Phase 1** (this task) | Core e-Fapiao: blue invoice, red form, vendor red forms, registration callback | Current |
| **Phase 2** (follow-up task) | Extended tax support / additional invoice type cases | TBD |
| **Phase 3** (follow-up task) | New endpoint implementation | TBD |
| **Beyond** | POS integration / adaptation | TBD |

---

## 14. Sandbox Credentials (Development Only)

```
Platform Login:  https://www-pre.baiwang.com
Username:        admin_rsmc17paj2ic8
Password:        Aa1234567Aa
App Key:         1004139
App Secret:      15719e2a-89b7-4032-acc0-ff62151d1bbb
Salt:            15258c22aa1349819e8cf20c0da04956
Tax No:          DB20240220YHCS1009
Company:         某刻股份有限公司测试109
Org Auth Code:   fDBe20324c02720rYH0CSl10i09wiiu2
Virtual OAC:     y01623e45x67k89dzy0xwlvuitswiiu3 (non-business interfaces only)
App IDs:         2676060529553834172, 2664365078056272044
```

> ⚠️ The `virtual orgAuthCode` (y01...) must NOT be used for business token retrieval. Use the real one (fDBe...) for invoice operations.

