{
    "name": "OD19 Sale Terms",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Reusable term/condition templates for sales quotations.",
    "description": """
OD19 Sale Terms
===============

Store standard terms and conditions for quotations (price, delivery,
payment - product/engineering, validity, warranty, credit) in reusable
templates that can be selected on a sale order and concatenated into a
single block of text for report display.

This consolidates the seven separate master report models from Odoo 15
into a single ``od19.sale.term.template`` model with a ``term_type``
selection field.
    """,
    "depends": ["sale_management", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_term_template_views.xml",
        "views/sale_order_views.xml",
        "report/sale_order_report.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sale_terms/static/description/icon.svg",
}
