# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'OpenID Authentification',
    'version': '2.0',
    'category': 'Tools',
    'description': """
Allow users to login through OpenID.
====================================
""",
    'author': 'OpenERP s.a.',
    'maintainer': 'OpenERP s.a.',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'web'],
    'data': [
        'res_users.xml',
        'views/auth_openid.xml',
    ],
    'qweb': ['static/src/xml/auth_openid.xml'],
    'external_dependencies': {
        'python' : ['openid'],
    },
    'installable': True,
    'auto_install': False,
}
