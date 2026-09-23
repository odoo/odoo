{
    "name": "WMS Accounting",
    "version": "1.3",
    "category": "Supply Chain/Inventory",
    "sequence": 16,
    "summary": "Inventory, Logistic, Valuation, Accounting",
    "description": """
WMS Accounting module
======================
This module makes the link between the 'stock' and 'account' modules and allows you to create accounting entries to value your stock movements

Key Features
------------
* Stock Valuation (periodical or automatic)
* Invoice from Picking

Dashboard / Reports for Warehouse Management includes:
------------------------------------------------------
* Stock Inventory Value at given date (support dates in the past)
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "account",
    ],
    "data": [
        "security/stock_account_security.xml",
        "security/ir.access.csv",
        "data/stock_account_data.xml",
        "views/account_account_views.xml",
        "views/stock_account_views.xml",
        "views/res_config_settings_views.xml",
        "views/report_invoice.xml",
        "views/stock_quant_views.xml",
        "views/product_views.xml",
        "views/product_value_views.xml",
        "views/stock_location_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_move_views.xml",
        "wizards/stock_inventory_adjustment_name_views.xml",
        "reports/account_invoice_report_view.xml",
        "reports/stock_avco_audit_report_views.xml",
        "reports/stock_valuation_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "stock_account/static/src/**/*",
        ],
    },
    "auto_install": True,
    "post_init_hook": "_post_init_hook",
}
