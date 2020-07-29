# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Colombian - Point of Sale Report',
    'version': '1.0',
    'description': """Colombian - Point of Sale""",
    'category': 'Localization',
    'auto_install': True,
    'depends': [
        'l10n_co',
        'point_of_sale',
        'l10n_co_pos'
    ],
    'data': [
        'views/templates.xml',
        'views/pos_config_views.xml',
        'wizard/pos_details_wizard_views.xml'
    ],
}
