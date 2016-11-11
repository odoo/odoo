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
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['stock_account', 'purchase'],
    'category': 'Warehouse',
    'sequence': 16,
    'demo': [
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/stock_landed_cost_data.xml',
        'views/product_views.xml',
        'views/stock_landed_cost_views.xml',
    ],
    'test': [
        '../account/test/account_minimal_test.xml',
        '../stock_account/test/stock_valuation_account.xml',
        'test/stock_landed_costs.yml',
        'test/stock_landed_costs_rounding.yml',
    ],
    'installable': True,
    'auto_install': False,
}
