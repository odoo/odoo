---
name: odoo-guidelines
description: >-
  House rules for Odoo addon code: module structure, manifest, Python/ORM,
  fields, controllers, XML views and data, QWeb reports, access rights and
  record rules, performance, tests. Use when writing or reviewing any file in
  an Odoo addon outside static/ (for the JavaScript, Owl templates and SCSS
  under static/, see odoo-web-guidelines).
---

# Odoo addon guidelines

House rules for code in Odoo addons (`addons/*` and `odoo/addons/*`).
Everything an addon ships under `static/` has its own skill:
`odoo-web-guidelines`.

Guidelines are grouped by domain, one file per domain in `guidelines/`, one section per
guideline. No rule outranks another. Read the sections that match the files you are
touching instead of loading whole files.

| Guideline | Read it when |
| --- | --- |
| [Module structure and file naming](guidelines/module_structure.md#module-structure-and-file-naming) | creating or moving files in an addon, or adding a module |
| [Manifest](guidelines/manifest.md#manifest) | touching `__manifest__.py` |
| [Imports](guidelines/python.md#imports) | writing Python anywhere in an addon |
| [Naming and model layout](guidelines/python.md#naming-and-model-layout) | naming a model, field, method or variable; laying out a model class |
| [Translate only static literals](guidelines/python.md#translate-only-static-literals) | user-facing strings in Python |
| [Recordsets, domains and context](guidelines/orm.md#recordsets-domains-and-context) | reading records, building domains, passing context |
| [Computes, onchange and constraints](guidelines/orm.md#computes-onchange-and-constraints) | computes, onchange, constraints, indexes, `create` overrides |
| [Methods and extension points](guidelines/orm.md#methods-and-extension-points) | adding a model method, or one another module will override |
| [Transactions and exceptions](guidelines/orm.md#transactions-and-exceptions) | cursors, commits, savepoints, `try`/`except` |
| [Fields](guidelines/fields.md#fields) | declaring or modifying field definitions |
| [Controllers](guidelines/controllers.md#controllers) | touching `controllers/` or `@route` |
| [Views, actions and data records](guidelines/xml.md#views-actions-and-data-records) | touching `views/`, `data/`, or any XML records |
| [Anchor view inheritance on names, never on position](guidelines/xml.md#anchor-view-inheritance-on-names-never-on-position) | extending or overriding an existing view |
| [QWeb PDF reports](guidelines/reports.md#qweb-pdf-reports) | report templates or `_get_report_values` |
| [Access rights](guidelines/security.md#access-rights) | touching `security/` (`ir.access.csv`, groups) |
| [Batch ORM calls](guidelines/performance.md#batch-orm-calls) | ORM calls (`create`/`search*`/aggregates) inside a loop |
| [Performance conventions](guidelines/performance.md#performance-conventions) | code that loops over records or filters query results |
| [Tests](guidelines/tests.md#tests) | touching `tests/` |
| [Changes in a stable version](guidelines/stable.md#changes-in-a-stable-version) | any change targeting a released branch rather than master |

To add or restructure a guideline, follow [AUTHORING.md](AUTHORING.md).
