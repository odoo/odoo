# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'OAuth2 Authentication',
    'version': '1.0',
    'category': 'Extra Tools',
    'description': """
Allow users to login through OAuth2 Provider.
=============================================
""",
    'maintainer': 'Odoo s.a.',
    'depends': ['base', 'web', 'base_setup', 'auth_signup'],
    'data': [
        'data/auth_oauth_data.xml',
        'data/auth_oauth_data.yml',
        'views/auth_oauth_views.xml',
        'views/res_users_views.xml',
        'views/res_config_views.xml',
        'views/auth_oauth_templates.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
