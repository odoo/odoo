# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'To-Do',
    'version': '1.0',
    'category': 'Productivity/To-Do',
    'website': 'https://www.odoo.com/app/notes', # TODO: Updtate to the url of the to-do app once it is created
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
        'data/mail_template_data.xml',
        'data/todo_template.xml',
        'views/todo_views.xml',
        ],
    'demo': [
        'data/note_demo.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': '_init_onboarding_todo',
    'assets': {
        'mail.assets_messaging': [
            'note/static/src/models/*.js',
        ],
        'web.assets_backend': [
            'note/static/src/components/**/*',
            'note/static/src/scss/note.scss',
            'note/static/src/views/**/*',
        ],
        'web.qunit_suite_tests': [
            'note/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
