# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Presence Control - Time Off',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Control Employees Presence - Time Off
=====================================
""",
    'depends': ['hr_presence', 'hr_holidays'],
    'data': [
        'views/hr_employee_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
}
