# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Added the Thai **Billing Note (ใบวางบิล)** QWeb PDF report in `od19_accounting_features` — groups the outstanding customer invoices of one partner into a single billing document with the amount in words and signature lines.
- Added the **Job Assignment Document (ใบมอบหมายงาน)** QWeb PDF report in `od19_project_enhanced` — prints job no, customer, department, project category, owner, responsible persons, coordinators, contractors, scope of work, document requirements and the linked sales order.
- Added OCA dependency repositories for the Wave 1 Sales baseline and formalized them as Git submodules for reproducible setup.

### Documentation
- Audited and modernized `GAP_ANALYSIS_OD15_to_OD19.md` with the current status of the code (2026-10-19): 22 IMPLEMENTED, 2 PARTIAL, 1 MISSING.
- Added a current-status audit note to `OCA_MODULE_ASSESSMENT_TH.md` (ส่วนที่ 3 — OCA Module Matching, เดิมคือ `OCA_MODULE_MATCHING.md`) pointing to the authoritative status table.
- Extended `od19_sales_oca_bridge_workflow` to support the required-now OCA baseline for blanket orders, sale revisions, and exception-driven controls.
- Added `docs/superpowers/programs/odoo19-enterprise/sales/oca-installation-recommendations.md` to map OCA sales modules into `Wave 1`, `Wave 2`, `Wave 3`, and `Deferred / Not now`.

### Changed
- Aligned Sales OCA baseline references across fit-gap, addon boundaries, baseline design, and the Wave 1 implementation plan.
- Updated the Wave 1 Sales Contract Core design to include explicit OCA installation guidance by wave.

### Fixed
- Tightened the OCA bridge baseline after review follow-ups so the required-now stack matches the approved baseline more closely.
- Cleaned up OCA bridge form semantics and related bridge tests to reduce UI ambiguity in the sales workflow.

### Documentation
- Added a documented shortlist for immediate OCA installation: `base_user_role`, `sale_blanket_order`, `base_revision`, `sale_order_revision`, `sale_delivery_state`, `base_exception`, and `sale_exception`.
- Documented the next recommended candidates for later waves: `sale_order_line_price_source`, `sale_invoice_to_partner`, `sale_invoice_blocking`, `sale_order_type`, `sale_invoice_frequency`, `sale_substate`, and `sale_cancel_reason`.
- Kept `sale_tier_validation` and `sale_invoice_plan` in deferred status pending clearer 19.0 baseline confirmation.
