{
    "name": "WMS Landed Costs",
    "version": "1.3",
    "category": "Supply Chain/Inventory",
    "sequence": 16,
    "summary": "Landed Costs",
    "description": """
Landed Costs Management
=======================
This module allows you to easily add extra costs on pickings and decide the split of these costs among their stock moves in order to take them into account in your stock valuation.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "purchase_stock",
    ],
    "data": [
        "security/ir.access.csv",
        "data/stock_landed_cost_data.xml",
        "views/account_move_views.xml",
        "views/product_views.xml",
        "views/stock_landed_cost_views.xml",
        "views/res_config_settings_views.xml",
        "views/stock_landed_costs_menus.xml",
    ],
}
