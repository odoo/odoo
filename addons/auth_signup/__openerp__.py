# -*- coding: utf-8 -*-

{
    'name': 'Signup',
    'description': """
Allow users to sign up and reset their password
===============================================
    """,
    'author': 'Odoo S.A.',
    'version': '1.0',
    'category': 'Authentication',
    'website': 'https://www.odoo.com',
    'depends': [
        'base_setup',
        'mail',
        'web',
    ],
    'data': [
        'data/auth_signup_data.xml',
        'views/auth_signup_templates.xml',
        'views/res_config.xml',
        'views/res_users_view.xml',
    ],
    'auto_install': True,
    'bootstrap': True,
    'installable': True,
}
