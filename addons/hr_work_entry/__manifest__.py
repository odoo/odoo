#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Work Entries',
    'category': 'Human Resources/Employees',
    'sequence': 39,
    'summary': 'Manage work entries',
    'installable': True,
    'depends': [
        'hr',
    ],
    'data': [
        'security/hr_work_entry_security.xml',
        'security/ir.model.access.csv',
        'data/hr_work_entry_data.xml',
        'views/hr_work_entry_views.xml',
        'views/hr_employee_views.xml',
        'views/resource_calendar_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_work_entry/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
