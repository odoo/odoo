# Patterns Index

Extracted: 2026-05-22 | Phase 5 of init-workspace-flow | Workspace: tx10-odoo (Odoo 19.0)

---

## ORM / Model Layer

| Pattern | File | One-line description |
|---------|------|----------------------|
| ORM Model | [orm-model-pattern.md](./orm-model-pattern.md) | Class structure for persistent business objects using `models.Model` |
| Field Definition | [field-definition-pattern.md](./field-definition-pattern.md) | Scalar, relational, computed, and related field declarations |
| API Decorator | [api-decorator-pattern.md](./api-decorator-pattern.md) | `@api.depends`, `@api.constrains`, `@api.onchange`, `@api.model_create_multi` |
| Domain / Filter | [domain-filter-pattern.md](./domain-filter-pattern.md) | List-form and `Domain` class syntax for ORM queries and record rules |
| Wizard / TransientModel | [wizard-transient-model-pattern.md](./wizard-transient-model-pattern.md) | Modal dialog pattern using `models.TransientModel` for batch operations |

---

## HTTP / Controller Layer

| Pattern | File | One-line description |
|---------|------|----------------------|
| HTTP Controller | [http-controller-pattern.md](./http-controller-pattern.md) | Route handlers for HTML pages, JSON-RPC endpoints, and REST routes |

---

## Frontend (OWL)

| Pattern | File | One-line description |
|---------|------|----------------------|
| OWL Component | [owl-component-pattern.md](./owl-component-pattern.md) | Reactive UI components: `Component`, `useState`, hooks, registry |

---

## Module System

| Pattern | File | One-line description |
|---------|------|----------------------|
| Module / Addon Structure | [module-addon-structure-pattern.md](./module-addon-structure-pattern.md) | Directory layout, `__manifest__.py`, `__init__.py`, load order |

---

## Security

| Pattern | File | One-line description |
|---------|------|----------------------|
| Security Model | [security-model-pattern.md](./security-model-pattern.md) | ACL CSV, record rules (`ir.rule`), groups, field-level `groups=` |

---

## Testing

| Pattern | File | One-line description |
|---------|------|----------------------|
| Test Case | [test-case-pattern.md](./test-case-pattern.md) | `TransactionCase`, `HttpCase`, `@tagged`, `setUpClass`, assertions |

---

## Source Traceability

| Pattern | Primary Source Files |
|---------|----------------------|
| ORM Model | `odoo/orm/models.py`, `addons/account/models/account_move.py:72`, `addons/account/models/account_tax.py:25` |
| Field Definition | `odoo/orm/fields.py`, `odoo/orm/fields_relational.py`, `addons/account/models/account_journal.py:95` |
| API Decorator | `odoo/api/`, `addons/account/models/account_move.py:803–2856` |
| Domain / Filter | `odoo/orm/domains.py:196`, `addons/account/models/account_move.py:2503`, `addons/sale/models/sale_order.py:471` |
| Wizard / TransientModel | `odoo/orm/models_transient.py`, `addons/account/wizard/` |
| HTTP Controller | `odoo/http.py`, `addons/calendar/controllers/main.py:9` |
| OWL Component | `addons/board/static/src/board_controller.js`, `addons/mrp_subcontracting/static/src/components/` |
| Module / Addon Structure | `addons/account/__manifest__.py`, `addons/account/__init__.py` |
| Security Model | `addons/website_event_track/security/ir.model.access.csv`, `addons/sale/security/ir_rules.xml` |
| Test Case | `odoo/tests/common.py:990`, `addons/base_address_extended/tests/test_street_fields.py`, `addons/account/tests/test_account_journal.py` |

---

## Reading Paths by Role

**New Python developer**
Start: orm-model-pattern → field-definition-pattern → api-decorator-pattern → domain-filter-pattern → test-case-pattern

**Frontend developer**
Start: module-addon-structure-pattern (assets section) → owl-component-pattern → http-controller-pattern

**DevOps / Solution architect**
Start: module-addon-structure-pattern → security-model-pattern → domain-filter-pattern

**Feature developer (full stack)**
All patterns in order: orm-model → field-definition → api-decorator → view-definition → wizard-transient-model → http-controller → owl-component → security-model → domain-filter → test-case
