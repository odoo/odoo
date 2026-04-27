#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payroll - Attendance',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Manage extra hours for your hourly paid employees using attendance',
    'installable': True,
    'auto_install': True,
    'depends': [
        'hr_work_entry_contract_attendance',
        'hr_payroll',
    ],
    'data': [
        'data/hr_payroll_attendance_data.xml',
        'views/hr_payroll_attendance_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'demo': [
        'data/hr_payroll_attendance_demo.xml',
    ],
    'license': 'OEEL-1',
}
