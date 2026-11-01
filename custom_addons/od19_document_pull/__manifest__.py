# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Document Pull",
    "version": "19.0.1.3.0",
    "author": "OD19",
    "category": "Accounting",
    "summary": "Central mechanism to pull source document lines into a "
    "destination form, with lineage-based removal and confirmation.",
    "license": "LGPL-3",
    "depends": [
        "account",
        "sale_management",
        "purchase",
        "purchase_stock",
        "purchase_request",
        "od19_purchase_wizards",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/od19_document_pull_wizard_views.xml",
        "views/account_move_views.xml",
        "views/purchase_order_views.xml",
        "report/grni_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_document_pull/static/description/icon.svg",
}
