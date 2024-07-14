# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Accounting Import',
    'summary': 'Improved Import in Accounting',
    'category': 'Accounting/Accounting',
    'description': """
Accounting Import
==================
    """,
    'depends': ['account_accountant', 'base_import'],
    'data': [
        'views/account_import_views.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'wizard/setup_wizards_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_base_import/static/src/js/**/*',
            'account_base_import/static/src/xml/**/*',
        ],
    }
}
