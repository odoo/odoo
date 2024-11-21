# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Remote Work',
    'version': '2.0',
    'category': 'Human Resources/Remote Work',
    'depends': ['hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/res_users.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'hr_homeworking/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
