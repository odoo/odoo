{
    "name": "Tax Computation Engine",
    "version": "19.0.1.3.0",
    "category": "Hidden",
    "summary": "Standalone tax computation for order types",
    "description": """
Tax Computation Engine
=======================

Canonical tax computation engine defining ``account.tax``, ``account.tax.group``,
and ``account.tax.repartition.line``.  The ``account`` module inherits from these
models (via ``_inherit``) to add accounting-specific fields and methods such as
journal accounts, tax tags, exigibility, and CABA handling.

Modules that need tax computation without the full accounting stack (e.g.
``base_order``, ``sale``, ``purchase``) can depend on ``account_tax`` directly.

Models:
-------
* **account.tax** — tax definition, rate computation, base line preparation
* **account.tax.group** — tax grouping for display and reporting
* **account.tax.repartition.line** — tax distribution factors

Key API:
--------
* ``_prepare_base_line_for_taxes_computation()`` — convert record → base_line dict
* ``_add_tax_details_in_base_lines()`` — compute tax amounts
* ``_round_base_lines_tax_details()`` — rounding pipeline
* ``_get_tax_totals_summary()`` — aggregate into display dict
* ``compute_all()`` — public tax computation API
    """,
    "author": "Odoo Community",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "product",
    ],
    "data": [
        "security/account_tax_security.xml",
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "account_tax/static/src/helpers/*.js",
        ],
        "web.assets_frontend": [
            "account_tax/static/src/helpers/*.js",
        ],
    },
}
