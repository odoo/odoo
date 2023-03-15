# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Notes',
    'version': '1.0',
    'category': 'Productivity/Notes',
    'website': 'https://www.odoo.com/app/notes',
    'summary': 'Organize your work with memos',
    'sequence': 260,
    'depends': [
        'mail',
    ],
    'data': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'data/note_data.xml',
        'data/res_users_data.xml',
        'views/note_views.xml',
        ],
    'demo': [
        'data/note_demo.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'note/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
