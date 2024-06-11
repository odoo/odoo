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
        'security/project_todo_security.xml',
        'data/mail_activity_type_data.xml',
        'data/todo_template.xml',
        'views/project_task_views.xml',
        'views/project_todo_menus.xml',
        'wizard/mail_activity_todo_create.xml',
    ],
    'installable': True,
    'application': True,
    'uninstall_hook': '_todo_uninstall',
    'assets': {
        'web.assets_backend': [
            'project_todo/static/src/components/**/*',
            'project_todo/static/src/scss/todo.scss',
            'project_todo/static/src/views/**/*',
            'project_todo/static/src/web/**/*',
        ],
    },
    'license': 'LGPL-3',
}
