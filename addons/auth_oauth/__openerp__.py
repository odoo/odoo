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
    'maintainer': 'OpenERP s.a.',
    'depends': ['base', 'web', 'base_setup', 'auth_signup'],
    'data': [
        'res_users.xml',
        'auth_oauth_data.xml',
        'auth_oauth_data.yml',
        'auth_oauth_view.xml',
        'security/ir.model.access.csv',
        'res_config.xml',
        'views/auth_oauth_login.xml',
    ],
    'installable': True,
    'auto_install': False,
}
