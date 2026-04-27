#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Attendances - Planning',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Create work entries from attendances based on employee\'s planning',
    'depends': [
        'hr_work_entry_contract_planning',
        'hr_work_entry_contract_attendance',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
