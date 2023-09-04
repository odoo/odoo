# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Peruvian - Point of Sale with PE Doc',
    'version': '1.0',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
This module brings the technical requirement for the Peruvian regulation.
Install this if you are using the Point of Sale app in Peru.
    """,
    'depends': [
        'l10n_pe',
        'point_of_sale',
    ],
    'data': [
        'data/res_partner_data.xml',
        'views/templates.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_pe_pos/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
