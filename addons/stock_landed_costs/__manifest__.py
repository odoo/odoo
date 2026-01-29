# -*- coding: utf-8 -*-
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
    'category': 'Inventory/Inventory',
    'sequence': 16,
    'data': [
        'security/ir.model.access.csv',
        'security/stock_landed_cost_security.xml',
        'data/stock_landed_cost_data.xml',
        'views/account_move_views.xml',
        'views/product_views.xml',
        'views/stock_landed_cost_views.xml',
        'views/stock_valuation_layer_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
