# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Work Entries',
    'category': 'Human Resources/Employees',
    'sequence': 39,
    'summary': 'Manage work entries',
    'depends': [
        'hr',
    ],
    'data': [
        'data/hr_work_entry_type_data.xml',
        'wizard/hr_work_entry_export_views.xml',
        'views/hr_work_entry_type_views.xml',
        'views/hr_employee_views.xml',
        'views/res_company_views.xml',
        'views/resource_calendar_views.xml',
        'views/menuitems.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'data/hr_work_entry_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_work_entry/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_work_entry/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
