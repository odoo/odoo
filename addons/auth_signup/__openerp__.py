# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Signup',
    'description': """
Allow users to sign up and reset their password
===============================================
    """,
    'author': 'OpenERP SA',
    'version': '1.0',
    'category': 'Authentication',
    'website': 'https://www.odoo.com',
    'installable': True,
    'auto_install': True,
    'depends': [
        'base_setup',
        'mail',
        'web',
    ],
    'data': [
        'auth_signup_data.xml',
        'res_config.xml',
        'res_users_view.xml',
        'views/auth_signup_login.xml',
    ],
    'bootstrap': True,
}
