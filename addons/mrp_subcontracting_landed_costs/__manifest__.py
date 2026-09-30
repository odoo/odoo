# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Landed Costs With Subcontracting order',
    'version': '1.0',
    'summary': 'Advanced views to manage landed cost for subcontracting orders',
    'description': """
This module allows users to more easily identify subcontracting orders when applying landed costs,
by also displaying the associated picking reference in the search view.
    """,
    'depends': ['stock_landed_costs', 'mrp_subcontracting'],
    'category': 'Supply Chain/Manufacturing',
    'data': [
        'views/stock_landed_cost_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
