# Copyright 2022 Jarsa
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Report Pending Transfers",
    "summary": """

    """,
    "author": "Jarsa",
    "website": "https://www.jarsa.com",
    "license": "LGPL-3",
    "category": "Installer",
    "version": "15.0.1.0.1",
    "depends": [
        "l10n_mx",
        "l10n_mx_edi",
        "purchase_request",
        "sale_management",
        "stock",
        "product",
        "resource",
        "mrp",
    ],
    "test": [],
    "data": [
        "views/pending_transfers_view.xml",
    ],
    "demo": [],
}
