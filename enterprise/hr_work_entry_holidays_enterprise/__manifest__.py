# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Time Off in Payslips Enterprise',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'sequence': 95,
    'summary': 'Manage Time Off in Payslips Enterprise',
    'description': """
Manage Time Off in Payslips
============================

This application allows you to integrate time off in payslips.
    """,
    'depends': ['hr_work_entry_holidays'],
    'data': [
        'views/hr_work_entry_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
