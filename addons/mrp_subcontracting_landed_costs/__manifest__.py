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
<<<<<<< ffab70180ead24f4c40e92593a021244fdae14a8
    'depends': ['stock_landed_costs', 'mrp_subcontracting'],
    'category': 'Supply Chain/Manufacturing',
||||||| ab3f85fe24ecfc7bea690f759399716f466eee7e
    'depends': ['stock_landed_costs', 'mrp_subcontracting'],
    'category': 'Manufacturing/Manufacturing',
=======
    'depends': ['mrp_landed_costs', 'mrp_subcontracting'],
    'category': 'Manufacturing/Manufacturing',
>>>>>>> 9a8249a6dd83c57efff2f2131f353830e4d60e68
    'data': [
        'views/stock_landed_cost_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
