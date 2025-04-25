# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Landed Costs On MO',
    'summary': 'Landed Costs on Manufacturing Order',
    'description': """
This module allows you to easily add extra costs on manufacturing order
and decide the split of these costs among their stock moves in order to
take them into account in your stock valuation.
    """,
    'depends': ['stock_landed_costs', 'mrp'],
    'category': 'Supply Chain/Manufacturing',
    'data': [
        'security/ir.model.access.csv',
        'security/mrp_landed_costs_security.xml',
        'views/stock_landed_cost_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
