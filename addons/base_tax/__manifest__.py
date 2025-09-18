{
    "name": "Tax Computation Engine",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Standalone tax computation for order types",
    "description": """
Tax Computation Engine
=======================

Standalone copy of the Odoo tax computation engine, extracted from the
``account`` module for use by ``base_order`` and other modules that need
tax computation without the full accounting stack.

Models:
-------
* **account.tax** — tax definition, rate computation, base line preparation
* **account.tax.group** — tax grouping for display and reporting
* **account.tax.repartition.line** — tax distribution factors

Key API:
--------
* ``_prepare_base_line_for_taxes_computation()`` — convert record → base_line dict
* ``_add_tax_details_in_base_lines()`` — compute tax amounts
* ``_get_tax_totals_summary()`` — aggregate into display dict
* ``compute_all()`` — public tax computation API

Phase 1 of tax engine extraction.  Phase 2 will make ``account`` depend
on this module and remove the duplication.
    """,
    "author": "Odoo Community",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "product",
    ],
}
