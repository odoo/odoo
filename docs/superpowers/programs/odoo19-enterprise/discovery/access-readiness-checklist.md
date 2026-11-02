# Access and Readiness Checklist

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/discovery/access-readiness-checklist.md` |
| Artifact owner | Program discovery lead |
| Artifact status | Active discovery baseline |
| Overall readiness | Partial |
| Review status | Refreshed 2026-11-02 — usable for Wave 1 planning; remaining evidence gaps tracked per section |
| Last updated | 2026-11-02 |

## Readiness State Legend

- `Ready`: access is approved, usable, and backed by evidence.
- `Partial`: some access exists, but required evidence, scope, or operational constraints are incomplete.
- `Blocked`: needed for discovery, but waiting on approval, credentials, or environment setup.
- `Not Started`: no evidence has been attached yet.
- `N/A`: explicitly not required for this program or domain.

## Evidence Requirements

- Each line item should capture the approver or provider, date confirmed, environment scope, and a link or reference to the evidence.
- When access is constrained, record the limitation explicitly, such as read-only, time-boxed, sanitized-only, or business-hours-only.
- If a requirement is blocked, capture the blocking owner and next action so program review can escalate quickly.

This checklist is the active access-readiness baseline for Wave 1 planning. `Partial`, `Blocked`, and `Not Started` items are still open work and must not be restated elsewhere as fully complete.

## Readiness Summary

| Area | Status | Notes |
| --- | --- | --- |
| Application Access | Ready | Admin, Developer Mode, and Technical access used for discovery and for the Odoo 15 → 19 migration; source evidence attached in the tracker below. |
| Infrastructure Access | Partial | Dev shell + `odoo.conf` confirmed on Windows (`c:\odoo-dev\odoo19`); read-only access to the Odoo 15 server was used to obtain dumps — formal approval record still open. |
| Data Access | Partial | Odoo 15 custom-format dumps obtained and stored in `migration/od15_export/`; sanitized-copy and formal extraction approval still open. |
| Source and Integration Access | Partial | `custom_addons/` and 22 pinned OCA submodules available in git; ops scripts present; integration inventory partly documented (ZKTeco, notifications). |
| Security and Risk Access | Partial | RBAC via OCA `base_user_role` + `od19_role_catalog`; secrets live in `odoo.conf`; formal security review of automations and secrets still open. |

## Application Access
- [x] Odoo 15 admin access confirmed
- [x] Developer mode access confirmed
- [x] Technical menu access confirmed

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Odoo 15 admin access confirmed | Ready | Prior discovery session confirmed admin access in Odoo 15 CE. | Program discovery lead | Add a durable evidence reference, such as screenshot or access approval record. |
| Developer mode access confirmed | Ready | Prior discovery used Developer Mode successfully. | Program discovery lead | Record the exact enablement path and account used. |
| Technical menu access confirmed | Ready | Prior technical scan used Technical menus for models, menus, and actions. | Program discovery lead | Attach menu-path evidence for auditability. |

## Infrastructure Access
- [ ] Read-only production access approved
- [ ] Clone or staging shell access approved
- [ ] Odoo configuration files available
- [ ] Addon paths available

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Read-only production access approved | Partial | Read-only access to the Odoo 15 Linux server (`/var/odoo`) was used to obtain the custom-format dumps now stored in `migration/od15_export/`. | Infrastructure owner | Attach the formal read-only approval record; migrate to a sanitized staging clone if production reads must be restricted. |
| Clone or staging shell access approved | Ready | Local Windows dev shell at `c:\odoo-dev\odoo19` is operational (venv `venv19`, `odoo.conf`, dev DB `odoo19_pdev`). | Infrastructure owner | Staging DB target `od15_stage` per the data migration plan (Task D1). |
| Odoo configuration files available | Ready | `c:\odoo-dev\odoo19\odoo.conf` (DB, addons_path, workers, http port, logfile) is tracked in the repo. | Infrastructure owner | Confirm the Odoo 15 production config separately for legacy parameter parity. |
| Addon paths available | Ready | `odoo.conf` → `addons_path` lists `addons`, `odoo/addons`, `custom_addons`, and 22 `third_party/oca/*` submodules. | Infrastructure owner | Reconcile with the legacy Odoo 15 addon layout during profiling. |

## Data Access
- [ ] Full database dump provided
- [ ] Sanitized copy provided
- [ ] Master data extraction approved

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Full database dump provided | Ready | Custom-format dumps in `migration/od15_export/`: `odoo_golive.dump` (158 MB, go-live set) and `od15_autoerp_prd.dump` (10 MB, ออโต้อินโฟ production). | DBA or infrastructure owner | Track checksum/SHA256 and the restore test on `od15_stage` (migration Phase 0). |
| Sanitized copy provided | Partial | The working target DB is `odoo19_pdev` on the local dev instance; a dedicated sanitized Odoo 15 clone is not yet materialised. | DBA or security owner | Materialise a sanitized `od15_stage` for profiling and wider reviewer access. |
| Master data extraction approved | Partial | Extraction notes exist under `migration/od15_export/`: `modules.txt`, `dtr_columns.txt`, `versions.txt`, `attach_files.txt`. | Data owner | Formal approval for product, partner, employee, and financial master-data extraction still needed. |

## Source and Integration Access
- [ ] Custom addon repositories available
- [ ] Deployment scripts available
- [ ] Integration inventory available
- [ ] Test credentials available where needed

### Verification Tracker

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| Custom addon repositories available | Ready | `custom_addons/` (100+ `od19_*` modules) tracked in git; 22 OCA submodules pinned under `third_party/oca/` via `.gitmodules`. | Engineering owner | Keep submodule SHAs pinned (verified 2026-11-02 — all clean at pinned revisions). |
| Deployment scripts available | Ready | Ops scripts in the repo root: `STEP-1-Update-Odoo19.ps1`, `STEP-2-Install-Odoo19.ps1`, `STEP-3-Start-Odoo19.ps1`, `STEP-4-Backup-Odoo19.ps1`, `run-tests.ps1`. | DevOps owner | Document the STEP sequence and any manual steps before cut-over. |
| Integration inventory available | Partial | Known integrations: ZKTeco time-attendance and multi-channel notifications (`od19_notification_multi_channel`); a full inventory of APIs, file drops, and sync jobs is not yet consolidated. | Integration owner | Consolidate the integration inventory before Wave 1 close. |
| Test credentials available where needed | Not Started | No credential-access process linked yet. | System owner | Use least-privilege; avoid sharing production credentials directly. |

## Security and Integration Access Readiness

| Requirement | State | Evidence or source | Owner | Blocker or notes |
| --- | --- | --- | --- | --- |
| High-risk automated actions review approved | Partial | Cron/automation surfaces present (e.g. `od19_notification_multi_channel`, ISO calibration cron); no consolidated review record yet. | Security or platform owner | Inventory server actions and cron jobs and record the review. |
| Secret and credential storage review approved | Partial | Secrets are centralised in `odoo.conf` (DB user/password, hashed `admin_passwd`); external secrets-storage policy not yet reviewed. | Security owner | Confirm where API keys, SMTP, bank, and shared secrets live and how they are rotated. |
| Service accounts and elevated users identified | Partial | RBAC is centralised via OCA `base_user_role` + `od19_role_catalog`; a full identity inventory is pending. | Security owner | Produce the identity inventory for auditability and least-privilege review. |
| Audit-log or operational log access approved | Ready | Server logging configured in `odoo.conf` (`logfile = C:\odoo-dev\odoo19\odoo_server.log`); logs are readable in the dev environment. | Infrastructure owner | Define retention and access policy for production logs. |
| External integration endpoints validated | Partial | ZKTeco device integration delivered (2026-10-15); other external endpoints not yet catalogued. | Integration owner | Capture owner, auth model, transport, and data sensitivity per endpoint. |

## Open Questions and Blockers

- Which owner approves read-only production access, and is there a preferred safer alternative such as staging or sanitized clone?
- Is there an approved evidence repository for screenshots, approvals, config extracts, and repository links used in this checklist?
- Are security owners comfortable exposing secrets indirectly through config review, or is a mediated walkthrough required instead?
- Which integrations require separate third-party approvals or test credentials before discovery can validate them?
