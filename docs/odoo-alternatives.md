
## Option 1: Odoo Community + build on `ir.attachment`

Odoo Community already has the primitives Documents wraps:

| Documents feature | Community equivalent |
|---|---|
| File storage | `ir.attachment` (with filestore, dedup by checksum) |
| Folder tree | Build a `document.folder` model (parent_id hierarchy) |
| Tags | `many2many` to a tag model — trivial |
| Access rights | `ir.rule` record rules + `ir.model.access` — **more powerful than Documents' group model**, and this is what you need for độ mật anyway |
| Email alias → document | `mail.alias` + `mail.thread` — Community feature |
| Chatter / activity | `mail.thread`, `mail.activity.mixin` — Community |
| Workflow automation | `base_automation` (Automated Actions) — Community. Studio's "Automation Rules" is just a UI over this |
| Versioning | Custom `document.version` model |
| Full-text search | PostgreSQL `tsvector` + GIN index, or pg_trgm |
| PDF split/merge | `pypdf` server action |
| Approvals | OCA `base_tier_validation` |

**This is the path I'd recommend.** You were going to custom-build the sổ văn bản đến/đi, cấp số, thể thức engine, and metadata schema regardless — Documents wasn't going to give you those. Building on `ir.attachment` means you own the data model and aren't fighting Enterprise's workspace abstraction.

Realistic effort: 3–5 person-months for a solid DMS core (folders, tags, versioning, record-level access by độ mật, full-text search, alias intake).

## Option 2: OCA modules (free, AGPL)

The Odoo Community Association maintains a `dms` repository:

- **`dms`** — directories, files, storage backends, access groups. The closest OCA analogue to Documents.
- **`dms_field`** — attach DMS directories to any record
- **`document_page`** — wiki-style documents with approval and revision history
- **`base_tier_validation`** — multi-step approval workflows (this covers your trình ký flow)
- **`report_qweb_*`** — report customization

Caveat: OCA `dms` maturity varies by version. Check whether it's been ported to your target Odoo version (18/19) before committing — OCA ports often lag 6–12 months.

## Option 3: External DMS + Odoo integration

Keep Odoo Community for workflow/tasks/calendar, put documents in a dedicated open-source DMS:

| System | Fit for your case |
|---|---|
| **Alfresco Community** | Java, mature, strong records-management (retention schedules, classification), CMIS API. Heavy but genuinely built for archival compliance — which matches thời hạn bảo quản requirements |
| **Nuxeo** | Similar class, good metadata modeling |
| **Paperless-ngx** | Python/Django, **built-in OCR pipeline** (Tesseract, supports `vie`), auto-tagging, full-text search. Lightweight. Excellent fit for the số hóa hồ sơ requirement specifically |
| **Mayan EDMS** | Python, document-centric, OCR, metadata, workflows, cabinets |
| **SeaweedFS / MinIO** | Just object storage — pair with your own metadata layer |

**Paperless-ngx deserves a serious look** for the OCR/số hóa portion — it solves the Vietnamese OCR gap I flagged earlier, out of the box.

## Option 4: Skip Odoo for the document layer entirely

Given that ~54% of your requirements were GAP against Odoo anyway, and the heaviest gaps (sổ văn bản, thể thức, chữ ký số PKI, liên thông tỉnh) are all custom work, consider whether Odoo is earning its place. A Django/FastAPI + PostgreSQL stack gives you full control and no license question. The tradeoff: you lose Odoo's free Calendar, Project, Contacts, and the admin UI scaffolding.

## Recommendation

**Odoo Community + custom DMS module built on `ir.attachment`, with Paperless-ngx or a Tesseract service handling OCR ingestion.**

Rationale:
1. You keep Community's Calendar, Project, Contacts, mail.thread, base_automation — all free, all useful.
2. `ir.rule` record-level security is what you actually need for độ mật; Documents' Read/Write Groups was already a PARTIAL FIT.
3. No Enterprise license cost, no per-user fee — significant for a phường/xã budget and for scaling to nhiều đơn vị.
4. AGPL Community can be self-hosted with full source access — matches data sovereignty requirements for cơ quan Đảng.

## Replacements for the other Enterprise modules you'd lose

| Enterprise | Community alternative |
|---|---|
| Sign | Custom PKI integration (you needed this anyway — Odoo Sign wasn't PKI-compliant) |
| Studio | Write modules directly, or OCA `base_custom_info` |
| Dashboards / Spreadsheet | OCA `web_dashboard_tile`, or Metabase/Superset alongside Odoo reading the same Postgres |
| AI features | Self-hosted LLM + custom server actions (required regardless for data sovereignty) |
| Appointments | `calendar` (Community) + custom booking, or OCA `calendar_*` modules |

One thing worth verifying before you commit: check the current OCA `dms` module status for your target Odoo version, and confirm your licensing posture — if any part of the system will be distributed to other units, AGPL obligations apply to your custom modules too.