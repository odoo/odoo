# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WMS Landed Costs',
    'version': '1.1',
    'summary': 'Landed Costs',
    'description': """
Landed Costs Management
=======================
This module allows you to easily add extra costs on pickings and decide the split of these costs among their stock moves in order to take them into account in your stock valuation.
    """,
    'depends': ['stock_account', 'purchase_stock'],
    'category': 'Supply Chain/Inventory',
    'sequence': 16,
    'data': [
        'data/stock_landed_cost_data.xml',
        'views/account_move_views.xml',
        'views/product_views.xml',
        'views/stock_landed_cost_views.xml',
        'views/res_config_settings_views.xml',
        'security/ir.access.csv',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
