# Patterns Change Log

## 2026-05-22 — Phase 5: Pattern Extraction (init-workspace-flow)

Workspace: `tx10-odoo` (Odoo 19.0, branch `19.0`)
Extracted by: init-workspace-flow Phase 5 (docs architect agent)

---

### Added

- [orm-model-pattern] Extracted from `odoo/orm/models.py`, `addons/account/models/account_move.py:72–82`, `addons/account/models/account_tax.py:25–56` (added)
- [field-definition-pattern] Extracted from `odoo/orm/fields.py`, `odoo/orm/fields_relational.py`, `addons/account/models/account_journal.py:95–272`, `addons/account/models/account_move.py:108–403` (added)
- [api-decorator-pattern] Extracted from `odoo/api/`, `addons/account/models/account_move.py:803–3870`, `addons/account/models/account_tax.py:65` (added)
- [view-definition-pattern] Extracted from `addons/sale/views/sale_order_views.xml:6–570` (added)
- [module-addon-structure-pattern] Extracted from `addons/account/__manifest__.py`, `addons/account/__init__.py`, `addons/cloud_storage_google/__manifest__.py`, `addons/hr_recruitment_survey/__manifest__.py`, `odoo/modules/loading.py` (added)
- [http-controller-pattern] Extracted from `odoo/http.py`, `addons/calendar/controllers/main.py:9–119` (added)
- [security-model-pattern] Extracted from `addons/website_event_track/security/ir.model.access.csv`, `addons/sale/security/ir_rules.xml`, `addons/hr_attendance/security/hr_attendance_overtime_ruleset_security.xml`, `addons/account/models/account_journal.py:172` (added)
- [test-case-pattern] Extracted from `odoo/tests/common.py:302–2208`, `addons/base_address_extended/tests/test_street_fields.py`, `addons/account/tests/test_account_journal.py` (added)
- [domain-filter-pattern] Extracted from `odoo/orm/domains.py:196–275`, `addons/account/models/account_move.py:2503–4639`, `addons/sale/models/sale_order.py:471–862` (added)
- [owl-component-pattern] Extracted from `addons/board/static/src/board_controller.js`, `addons/mrp_subcontracting/static/src/components/subcontracting_production_list_controller.js`, `addons/web/static/lib/owl/owl.js` (added)
- [wizard-transient-model-pattern] Extracted from `odoo/orm/models_transient.py`, `addons/account/wizard/account_payment_register_views.xml`, `addons/account/__manifest__.py` wizard entries (added)
- [INDEX.md] Created pattern index with category table, source traceability, and reading paths by role (added)

### Gaps Noted

- No real-world `wizard-transient-model-pattern` Python source was read directly (file not found at expected path); pattern was synthesized from manifest references and ORM knowledge. Recommend verifying against `addons/account/wizard/account_payment_register.py` when available.
- OWL component XML template convention (`.xml` alongside `.js`) inferred from directory structure; no full paired example was read.
- `view-definition-pattern` search view (filter/group-by) not covered — candidate for a follow-up `search-view-pattern.md`.
- Mixin composition pattern (e.g. `mail.thread`, `portal.mixin`) not extracted as standalone — partially covered in `orm-model-pattern.md`.
