{
    "name": "OD19 Purchase Terms",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Purchases",
    "summary": "Reusable term templates for purchase orders and vendor list price auto-fill.",
    "description": """
OD19 Purchase Terms
===================

Store standard terms for PO/PR (warranty, delivery to, payment term,
shipment, weight) in reusable templates, and auto-fill the list price on
purchase order lines from the vendor's product supplier info.

This consolidates the five separate master report models into a single
``od19.purchase.term.template`` model with a ``term_type`` selection field.
    """,
    "depends": ["purchase", "purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_term_template_views.xml",
        "views/purchase_order_views.xml",
        "report/purchase_order_report.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_purchase_terms/static/description/icon.svg",
}
