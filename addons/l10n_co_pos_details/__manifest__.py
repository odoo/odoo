# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Colombian - Point of Sale Details',
    'version': '1.0',
    'description': """Colombian - Point of Sale""",
    'category': 'Localization',
    'auto_install': True,
    'depends': [
        'l10n_co_pos'
    ],
    'data': [
        'wizard/pos_details.xml',
        'views/templates.xml',
        'views/pos_config_views.xml',
    ],
}
