# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Purchase Wizards",
    "version": "19.0.1.1.0",
    "category": "Purchase Management",
    "summary": "Trade discount wizard, PR line pricing, vendor/your ref on PR, "
    "and create vendor bill from PO wizard.",
    "author": "OD19",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "purchase_request",
        "account",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_request_views.xml",
        "views/purchase_order_views.xml",
        "wizards/purchase_trade_discount_views.xml",
        "wizards/purchase_create_vendor_bill_views.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_purchase_wizards/static/description/icon.svg",
}
