{
    "name": "To-Do",
    "version": "1.0",
    "category": "Productivity/To-Do",
    "sequence": 260,
    "summary": "Organize your work with memos and to-do lists",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "project",
    ],
    "data": [
        "security/ir.access.csv",
        "data/todo_template.xml",
        "views/project_task_views.xml",
        "views/project_todo_menus.xml",
        "wizards/mail_activity_todo_create.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_todo/static/src/components/**/*",
            "project_todo/static/src/scss/todo.scss",
            "project_todo/static/src/views/**/*",
            "project_todo/static/src/web/**/*",
        ],
        "web.assets_tests": [
            "project_todo/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "project_todo/static/tests/**/*",
        ],
    },
    "application": True,
    "auto_install": True,
    "post_init_hook": "_todo_post_init",
}
