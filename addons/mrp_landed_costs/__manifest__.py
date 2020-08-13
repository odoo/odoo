# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Landed Costs On MO',
    'version': '1.0',
    'summary': 'Landed Costs on Manufacturing Order',
    'description': """
This module allows you to easily add extra costs on manufacturing order 
and decide the split of these costs among their stock moves in order to 
take them into account in your stock valuation.
    """,
    'depends': ['stock_landed_costs', 'mrp'],
    'category': 'Manufacturing/Manufacturing',
    'data': [
        'views/stock_landed_cost_views.xml',
    ],
    'auto_install': True,
}
