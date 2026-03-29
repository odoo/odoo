# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Notes',
    'version': '1.0',
    'category': 'Productivity/Notes',
    'description': "",
    'summary': 'Organize your work with memos',
    'sequence': 260,
    'depends': [
        'mail',
    ],
    'data': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_data.xml',
        'data/note_data.xml',
        'data/res_users_data.xml',
        'views/note_views.xml',
        ],
    'demo': [
        'data/note_demo.xml',
    ],
    'test': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'note/static/src/scss/note.scss',
            'note/static/src/js/systray_activity_menu.js',
        ],
        'web.qunit_suite_tests': [
            'note/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'note/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
