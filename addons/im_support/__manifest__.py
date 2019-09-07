# -*- coding: utf-8 -*-
{
    'name': 'Livechat Support',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
        This module allows employee users to communicate with livechat operators
        of another database on which a counterpart addon is installed.
    """,
    'author': 'Odoo SA',
    'depends': [
        'mail',
    ],
    'data': [
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/discuss.xml",
        "static/src/xml/systray.xml",
    ],
    'installable': True,
    'auto_install': False,
}
