# -*- coding: utf-8 -*-
{
    'name': "Hide Odoo Brand In User Account Menu",
    'version': '16.0.1.0',

    "author": "ByteLegion",
    "website": "http://www.bytelegions.com",
    'company': 'ByteLegion',
    'maintainer': 'Waqar Ahmad',
    
    'depends': ['base'],
    'license': 'LGPL-3',
    "category": 'Tools',

    'summary': """Remove Documentation, Support, My Odoo.com account from the top right corner""",
    'description': """ Remove Documentation, Support, My Odoo.com account from the top right corner """,

    'assets': {
        'web.assets_backend': [
            'legion_hide_odoo/static/src/js/extended_user_menu.js',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
    
}
