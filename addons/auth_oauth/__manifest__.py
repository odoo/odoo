# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OAuth2 Authentication',
    'category': 'Tools',
    'description': """
Allow users to login through OAuth2 Provider.
=============================================
""",
    'maintainer': 'Odoo S.A.',
    'depends': ['base', 'web', 'base_setup', 'auth_signup'],
    'data': [
        'data/auth_oauth_data.xml',
        'data/auth_oauth_data.yml',
        'views/auth_oauth_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/auth_oauth_templates.xml',
        'security/ir.model.access.csv',
    ],
}
