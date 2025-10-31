# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'To-Do',
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
        'data/todo_template.xml',
        'views/project_task_views.xml',
        'views/project_todo_menus.xml',
        'wizard/mail_activity_todo_create.xml',
    ],
    'application': True,
    'post_init_hook': '_todo_post_init',
    'assets': {
        'web.assets_backend': [
            'project_todo/static/src/components/**/*',
            'project_todo/static/src/scss/todo.scss',
            'project_todo/static/src/views/**/*',
            'project_todo/static/src/web/**/*',
            'project_todo/static/src/webclient/**/*',
        ],
        'web.assets_tests': [
            'project_todo/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'project_todo/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
