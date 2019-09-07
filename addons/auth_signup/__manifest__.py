# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Signup',
    'description': """
Allow users to sign up and reset their password
===============================================
    """,
    'version': '1.0',
    'category': 'Extra Tools',
    'auto_install': True,
    'depends': [
        'base_setup',
        'mail',
        'web',
    ],
    'data': [
        'data/auth_signup_data.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/auth_signup_login_templates.xml',
        'views/auth_signup_assets.xml',
    ],
    'bootstrap': True,
}
