# Copyright 2022 Jarsa
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Instance Creator",
    "summary": """
    Instance creator for trinitate. This is the app.
    """,
    "author": "Jarsa",
    "website": "https://www.jarsa.com",
    "license": "LGPL-3",
    "category": "Installer",
    "version": "15.0.1.0.3",
    "depends": [
        "l10n_mx",
        "l10n_mx_edi",
        "purchase_request",
        "sale_management",
        "stock",
    ],
    "test": [],
    "data": [
        "views/account_analytic_tag.xml",
        "views/purchase_request_view.xml",
        "views/res_users_view.xml",
        "views/sale_order_view.xml",
        "views/stock_move_view.xml",
        "reports/report_sale_order.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
