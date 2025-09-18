# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OAuth2 Authentication',
    'version': '1.1',
    'category': 'Hidden/Tools',
    'description': """
Allow users to login through OAuth2 Provider.
=============================================
""",
    'depends': ['auth_signup'],
    'data': [
        'data/auth_oauth_data.xml',
        'views/auth_oauth_views.xml',
        'views/res_config_settings_views.xml',
        'views/auth_oauth_templates.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'auth_oauth/static/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
