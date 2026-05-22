# Project Context

**Workspace:** tx10-odoo | **Branch:** 19.0 (FINAL) | **Status:** Active maintenance

---

## What is Odoo?

Odoo is an open-source suite of web-based business applications built as a modular ERP/CRM platform. It covers the full business operation lifecycle — from customer relationship management and sales to accounting, inventory, manufacturing, human resources, and e-commerce — all within a single integrated platform. Odoo's defining characteristic is its modular architecture: applications can be installed independently as stand-alone tools or combined to form a complete enterprise resource planning system, with seamless data sharing across modules.

The platform is licensed under LGPL v3, making the core framework and community modules freely available. Odoo S.A. (the Belgian company behind the project) maintains both a community edition (this repository) and an Enterprise edition with additional proprietary modules. The community edition has an active global contributor base and is used by hundreds of thousands of organizations worldwide.

---

## This Repository

This repository is the **Odoo 19.0 community edition** source code. It contains the complete Odoo framework and all 622+ community business modules. The `19.0` branch represents a **FINAL release** — meaning it receives only patch-level fixes (bug fixes, security patches) and no new features. New features target the `master` branch.

- **Official source:** [github.com/odoo/odoo](https://github.com/odoo/odoo)
- **Official docs:** [odoo.com/documentation/19.0](https://www.odoo.com/documentation/19.0)
- **Developer tutorials:** [odoo.com/documentation/19.0/developer/howtos.html](https://www.odoo.com/documentation/19.0/developer/howtos.html)
- **Community forum:** [odoo.com/forum/help-1](https://www.odoo.com/forum/help-1)
- **License:** LGPL-3

---

## Key Business Modules

The `addons/` directory contains 622 community modules organized by business domain:

| Domain | Representative Modules |
|--------|------------------------|
| **Finance & Accounting** | account, account_accountant, account_edi, account_tax_python |
| **Sales & CRM** | sale, sale_management, crm, sale_loyalty, sale_coupon |
| **Inventory & Warehouse** | stock, purchase, mrp, stock_delivery |
| **Human Resources** | hr, hr_payroll, hr_attendance, hr_expense, hr_holidays |
| **Project & Productivity** | project, timesheet, mail, discuss, calendar |
| **E-commerce & Website** | website, website_sale, payment, e-commerce |
| **Manufacturing** | mrp, mrp_subcontracting, quality |
| **Point of Sale** | point_of_sale, pos_accounting |
| **Marketing** | mass_mailing, social, sms |
| **Localization** | l10n_* (country-specific tax, accounting, payroll rules) |

---

## Target Users & Use Cases

- **Small-to-medium businesses (SMBs):** Replacing fragmented tools (spreadsheets, standalone accounting, separate CRM) with a single integrated platform
- **Enterprise deployments:** Multi-company, multi-currency, multi-warehouse operations with complex accounting requirements
- **System integrators & partners:** Building custom modules, deploying managed Odoo instances for clients
- **Developers & contributors:** Extending core functionality via the module system, contributing upstream patches

---

## Community & Governance

- **Maintainer:** Odoo S.A. (Belgium) with global contributor network
- **License:** LGPL v3 — community modules are open; Enterprise modules are proprietary
- **Contribution model:** CLA (Contributor License Agreement) required for upstream contributions
- **Branch strategy:** One branch per major version (`14.0`, `15.0`, `16.0`, `17.0`, `18.0`, `19.0`, `master`)
- **Current branch:** `19.0` — FINAL release, patch fixes only

---

## Research Focus

This instance is being evaluated for **AI-first capabilities** in enterprise systems design:

### Research Questions
- How can Odoo become an AI-first CRM/ERP system?
- Where do LLM APIs (Claude, GPT, etc.) integrate most naturally into Odoo workflows?
- What custom field types and patterns enable AI-driven predictions and automations?

### Deployment Context
- **Stage:** Learning & Research + Development/Testing (NOT production)
- **Configuration:** Fresh clone, no business modules configured yet
- **CI/CD:** None required (research phase)
- **Focus:** Exploration and pattern documentation

### Candidate Integration Areas
- **AI field computation:** Fields that use LLM APIs to auto-populate values (summaries, classifications, predictions)
- **Workflow automation with AI decisions:** LLM-guided state transitions and business rule automation
- **Custom field types:** Data types for storing and rendering AI outputs (embeddings, classifications, structured JSON)
- **Prompt engineering patterns:** Context building with Odoo business data (customer history, record state, relationships)
- **Async API patterns:** Non-blocking integration with external LLM services during model compute/action execution

### Documentation Evolution
This documentation is evolving to support AI-integration research goals. New pattern files and architecture insights will be added as they emerge from exploration.

---

## Related Documentation

- [docs/TECHSTACK.md](./TECHSTACK.md) — Python/PostgreSQL/Werkzeug version matrix
- [docs/CODEMAP.md](./CODEMAP.md) — Directory structure and module organization
- [docs/DEPENDENCIES.md](./DEPENDENCIES.md) — Full dependency list with version constraints
