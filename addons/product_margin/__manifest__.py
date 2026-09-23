{
    "name": "Margins by Products",
    "category": "Sales/Sales",
    "description": """
Adds a reporting menu in products that computes sales, purchases, margins and other interesting indicators based on invoices.
=============================================================================================================================

The wizard to launch the report has several options to help you get the data you need.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.access.csv",
        "wizards/product_margin_view.xml",
        "views/product_product_views.xml",
        "views/product_margin_menus.xml",
    ],
}
