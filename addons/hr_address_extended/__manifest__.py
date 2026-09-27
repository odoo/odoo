# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Address Extended',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Centralize employee information',
    'website': 'https://www.odoo.com/app/employees',
    'depends': [
        'hr',
        'base_address_extended'
    ],
    'data': [
        'views/hr_employee_views.xml'
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
