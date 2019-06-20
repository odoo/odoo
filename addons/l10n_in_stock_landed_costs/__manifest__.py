# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - WMS Landed Costs',
    'version': '1.0',
    'description': """GST Landed Costs""",
    'category': 'Localization',
    'depends': [
        'stock_landed_costs',
        'l10n_in',
    ],
    'data': [
        'views/stock_landed_cost_views.xml',
    ],
    'auto_install': True,
}
