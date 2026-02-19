# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hide Powered By Odoo',
    'version': '15.0.1.0.0',
    'sequence': 1,
    'summary': """
        Hide Powered By Odoo login screen, Remove Powered By Odoo Login Page, Web Responsive login, Odoo Web Login Page, 
        Web backend login, Odoo login, Hide Powered By Odoo login screen, Remove Odoo, Sign-up Odoo, SignUp Form Login, 
        Hide Powered By Odoo SignIn screen, Remove Powered By Odoo SignUp Page, Web Responsive SignIn, Odoo Web SignIn Page, 
        Web backend SignIn, Remove Odoo SignUp Page, Odoo SignIn Page, Odoo Authentication Screen, Customize Login Page, 
        Hide Odoo, Disable Powered By Odoo in Login Page, Disable Odoo Powered By Login, Web Odoo Login Page Odoo Page Login,
    """,
    'description': "Hide Powered By Odoo in login screen.",
    'author': 'Innoway',
    'maintainer': 'Innoway',
    'price': '0.0',
    'currency': 'USD',
    'website': 'https://innoway-solutions.com',
    'license': 'LGPL-3',
    'images': [
        'static/description/wallpaper.png'     
    ],
    'depends': [
        'web'
    ],
    'data': [
        'views/login_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
