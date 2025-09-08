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
        'data/hr_work_entry_type_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_work_entry_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_template_views.xml',
        'views/resource_calendar_views.xml',
        'wizard/hr_work_entry_regeneration_wizard_views.xml',
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
