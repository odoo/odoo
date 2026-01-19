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
        'security/hr_work_entry_security.xml',
        'security/ir.model.access.csv',
        'data/hr_work_entry_type_data.xml',
        'views/hr_work_entry_type_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_template_views.xml',
        'views/resource_calendar_views.xml',
        'views/menuitems.xml',
    ],
    'demo': [
        'data/hr_work_entry_demo.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
