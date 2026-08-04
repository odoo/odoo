# Gentosai Garment Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers/executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add garment production stages to Odoo 19 Manufacturing Orders without duplicating Odoo inventory, BOM, or product-variant logic.

**Architecture:** New `gentosai_garment` addon depends on `mrp` and inherits `mrp.production`. One stored stage field and one server action advance work from cutting through packing; Odoo core remains responsible for BOM consumption and finished-stock updates.

**Tech Stack:** Odoo 19 Community, Python 3.11, PostgreSQL, XML views, Odoo `TransactionCase`.

## Global Constraints

- Keep upstream Odoo core unchanged.
- Put all custom code under `custom_addons/gentosai_garment`.
- Reuse Odoo `product`, `stock`, and `mrp`; no duplicate product, BOM, stock, or production-order models.
- Stage order: pending, cutting, sewing, finishing, packing, done.
- Only confirmed or in-progress Manufacturing Orders may advance.

---

### Task 1: Garment stage behavior

**Files:**
- Create: `custom_addons/gentosai_garment/__init__.py`
- Create: `custom_addons/gentosai_garment/__manifest__.py`
- Create: `custom_addons/gentosai_garment/tests/__init__.py`
- Create: `custom_addons/gentosai_garment/tests/test_garment_workflow.py`
- Create: `custom_addons/gentosai_garment/models/__init__.py`
- Create: `custom_addons/gentosai_garment/models/mrp_production.py`

**Interfaces:**
- Consumes: Odoo model `mrp.production`.
- Produces: field `garment_stage`; method `action_advance_garment_stage()`.

- [ ] **Step 1: Write failing transaction tests**

Test initial stage, strict stage ordering, and rejection while Manufacturing Order is still draft.

- [ ] **Step 2: Run RED test**

Run: `./odoo-bin -d gentosai_odoo_test --addons-path=addons,custom_addons -i gentosai_garment --test-enable --test-tags /gentosai_garment --stop-after-init`

Expected: failure because `mrp.production` has no `garment_stage` or `action_advance_garment_stage`.

- [ ] **Step 3: Add minimal inherited model**

Define six selection values, default `pending`, and one ordered transition method guarded by `UserError` for invalid Odoo states.

- [ ] **Step 4: Run GREEN test**

Run same command. Expected: 0 failures and exit 0.

### Task 2: Manufacturing Order UI

**Files:**
- Create: `custom_addons/gentosai_garment/views/mrp_production_views.xml`
- Modify: `custom_addons/gentosai_garment/__manifest__.py`

**Interfaces:**
- Consumes: `garment_stage`, `action_advance_garment_stage()`.
- Produces: stage field in MO list/form and `Tahap Berikutnya` form button.

- [ ] **Step 1: Add inherited list/form views**

Insert `garment_stage` after `product_id` in list and after `product_qty` in form. Add object button in form header, hidden for draft/cancel/done Odoo states or completed garment workflow.

- [ ] **Step 2: Validate addon install and XML**

Run module install test command. Expected: registry loads, views validate, 0 failures.

### Task 3: Verification and delivery

**Files:**
- Create: `docs/audits/odoo-19-structure.md`

- [ ] **Step 1: Record audit evidence**

Document Odoo version, Python/PostgreSQL compatibility, repository boundaries, relevant core addons, runtime prerequisites, and custom addon policy.

- [ ] **Step 2: Run syntax and addon tests**

Run `python -m compileall custom_addons/gentosai_garment`, XML parse checks, manifest parse check, and Odoo tagged test.

- [ ] **Step 3: Commit and push**

Commit verified files on `feat/gentosai-garment-workflow`, push to `gentosai404/odoo`, and report branch/commit/test evidence.
