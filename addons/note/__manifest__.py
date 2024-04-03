# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Notes',
    'version': '1.0',
    'category': 'Productivity/Notes',
    'summary': 'Organize your work with memos',
    'sequence': 260,
    'depends': [
        'mail',
    ],
    'data': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
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
        'mail.assets_messaging': [
            'note/static/src/models/*.js',
        ],
        'web.assets_backend': [
            'note/static/src/components/**/*',
            'note/static/src/scss/note.scss',
        ],
        'web.qunit_suite_tests': [
            'note/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
