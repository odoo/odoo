# -*- coding: utf-8 -*-

{
    'name': 'OpenID Authentification',
    'version': '2.0',
    'category': 'Tools',
    'description': """
Allow users to login through OpenID.
====================================
""",
    'author': 'Odoo S.A.',
    'maintainer': 'Odoo S.A.',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'web'],
    'data': [
        'views/res_users.xml',
        'views/auth_openid.xml',
    ],
    'qweb': ['static/src/xml/auth_openid.xml'],
    'external_dependencies': {
        'python': ['openid'],
    },
    'installable': True,
    'auto_install': False,
}
