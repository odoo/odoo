# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Planning Time Off',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 50,
    'summary': 'Planning integration with holidays',
    'depends': ['planning', 'hr_holidays_gantt'],
    'description': """
Planning integration with time off
""",
    'data': [
        'views/planning_slot_views.xml',
        'report/planning_report_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
