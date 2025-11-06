{
    'name': "Task Manager",
    'author': "Odoo",
    'website': "https://www.odoo.com/",
    'version': '0.1',
    'application': True,
    'installable': True,
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'task_manager/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'task_manager/static/tests/**/*'
        ]
    },
    'license': 'AGPL-3'
}
