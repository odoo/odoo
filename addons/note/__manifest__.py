# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'To-Do',
    'version': '1.0',
    'category': 'Productivity/To-Do',
    'website': 'https://www.odoo.com/app/todo', #NOTE: Is this page automatically created ??
    'summary': 'Organize your work with memos and to-do lists',
    'sequence': 260,
    'depends': [
        'mail',
    ],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'security/note_security.xml',
        'data/mail_activity_type_data.xml',
        'data/note_data.xml',
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
            'note/static/src/views/**/*',
#            'note/static/src/views/**/*.js',
#            'note/static/src/views/**/*.xml',
        ],
        'web.qunit_suite_tests': [
            'note/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
