#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Work Entries - Attendance',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Create work entries from the employee\'s attendances',
    'post_init_hook': '_generate_attendances',
    'depends': [
        'hr_work_entry_contract',
        'hr_attendance',
    ],
    'data': [
        'views/hr_contract_views.xml',
    ],
    'demo': [
        'data/hr_work_entry_contract_attendance_demo.xml',
    ],
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': True,
}
