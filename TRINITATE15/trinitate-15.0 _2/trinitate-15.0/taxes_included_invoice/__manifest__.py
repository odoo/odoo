# Copyright 2023 Jarsa
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "taxes included invoice",
    "summary": """
    taxes included invoice for trinitate.
    """,
    "author": "Jarsa",
    "website": "https://www.jarsa.com",
    "license": "LGPL-3",
    "category": "Installer",
    "version": "15.0.1.0.0",
    "depends": [
        "sale_stock",
        "sale_management",
    ],
    "test": [],
    "data": [
        "wizard/sale_make_invoice_advance_views.xml",
    ],
}
