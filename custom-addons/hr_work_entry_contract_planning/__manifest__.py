#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Work Entries - Planning',
    'category': 'Human Resources/Employees',
    'sequence': 95,
    'summary': 'Create work entries from the employee\'s planning',
    'installable': True,
    'auto_install': True,
    'depends': [
        'hr_work_entry_contract_enterprise',
        'planning',
    ],
    'data': [
        'views/hr_contract_views.xml',
    ],
    'demo': [
        'data/hr_work_entry_contract_planning_demo.xml',
    ],
    'license': 'OEEL-1',
}
