{
    "name": "Base Order Stock Integration",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Stock/delivery tracking mixins for order types",
    "description": """
Base Order Stock Integration
=============================

Bridge module connecting ``base_order`` with ``stock``.  Provides abstract
mixins for delivery/receipt tracking shared between sale_stock and
purchase_stock.

Mixins:
-------
* **order.stock.mixin** — transfer status, effective date, incoterms
* **order.line.stock.mixin** — qty_to_transfer, stock move helpers

The order-level ``_compute_transfer_state`` is IDENTICAL between sale_stock
and purchase_stock — only ``_compute_date_effective`` differs (customer
location filter for sale, non-supplier for purchase).
    """,
    "author": "Odoo Community",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "base_order",
        "stock",
    ],
}
