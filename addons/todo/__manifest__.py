# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'To-Do',
    'version': '1.0',
    'category': 'Productivity/To-Do',
    'summary': 'Organize your work with memos and to-do lists',
    'sequence': 260,
    'depends': [
        'project',
    ],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'security/todo_security.xml',
        'data/mail_activity_type_data.xml',
        'views/project_task_views.xml',
        'views/todo_menus.xml',
    ],
    'installable': True,
    'application': True,
    'uninstall_hook': '_todo_uninstall',
    'assets': {
        'web.assets_backend': [
            'todo/static/src/scss/todo.scss',
            'todo/static/src/views/**/*',
            'todo/static/src/web/**/*',
        ],
        'web.qunit_suite_tests': [
            'todo/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
