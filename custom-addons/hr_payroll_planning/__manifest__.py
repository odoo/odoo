#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payroll - Planning',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Manage extra hours for your hourly paid employees using planning',
    'installable': True,
    'auto_install': True,
    'depends': [
        'hr_work_entry_contract_planning',
        'hr_payroll',
    ],
    'data': [
        'views/hr_payslip_views.xml',
    ],
    'license': 'OEEL-1',
}
