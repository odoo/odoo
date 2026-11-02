# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Sale Wizards",
    "version": "19.0.1.1.0",
    "summary": (
        "Change delivery date wizard and downpayment invoice linking; "
        "invoice-line pulling is delegated to od19_document_pull"
    ),
    "author": "OD19",
    "category": "Sales",
    "depends": [
        "sale_management",
        "account",
        "sale_purchase",
        "od19_document_pull",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "wizards/sale_change_delivery_date_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_sale_wizards/static/description/icon.svg",
}
