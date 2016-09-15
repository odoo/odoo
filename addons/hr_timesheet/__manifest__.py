# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Timesheets',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 23,
    'description': """
This module implements a timesheet system.
==========================================

Each employee can encode and track their time spent on the different projects.

Lots of reporting on time and employee tracking are provided.

It is completely integrated with the cost accounting module. It allows you to set
up a management by affair.
    """,
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['account', 'hr', 'project'],
    'data': [
        'security/hr_timesheet_security.xml',
        'security/ir.model.access.csv',
        'hr_timesheet_view.xml',
        'project_timesheet_view.xml',
        'report/hr_timesheet_report_view.xml',
        'report/report_timesheet_templates.xml',
        'hr_timesheet_installer.xml',
        'hr_dashboard.xml',
    ],
    'demo': [
        'hr_timesheet_demo.yml',
    ],
    'test': [
        '../account/test/account_minimal_test.xml',
        'test/hr_timesheet_users.yml',
        'test/worktask_entry_to_timesheetline_entry.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
