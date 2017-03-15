# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Timesheets',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 23,
    'summary': 'Review and approve employees time reports',
    'description': """
This module implements a timesheet system.
==========================================

Each employee can encode and track their time spent on the different projects.

Lots of reporting on time and employee tracking are provided.

It is completely integrated with the cost accounting module. It allows you to set
up a management by affair.
    """,
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['hr', 'project'],
    'data': [
        'security/hr_timesheet_security.xml',
        'security/ir.model.access.csv',
        'hr_timesheet_view.xml',
        'hr_timesheet_config_settings_views.xml',
        'project_timesheet_view.xml',
        'report/hr_timesheet_report_view.xml',
        'report/report_timesheet_templates.xml',
        'hr_timesheet_installer.xml',
        'hr_dashboard.xml',
        'views/hr_views.xml',
    ],
    'demo': [
        'demo/hr_timesheet_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
