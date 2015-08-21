# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WMS Landed Costs',
    'version': '1.1',
    'author': 'Odoo SA',
    'summary': 'Landed Costs',
    'description': """
Landed Costs Management
=======================
This module allows you to easily add extra costs on pickings and decide the split of these costs among their stock moves in order to take them into account in your stock valuation.
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['purchase'],
    'category': 'Warehouse Management',
    'sequence': 16,
    'data': [
        'security/ir.model.access.csv',
        'data/stock_landed_costs_sequence.xml',
        'data/stock_landed_costs_data.xml',
        'views/product_views.xml',
        'views/stock_landed_costs_views.xml',
    ],
}
