# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheets and Time Off Automation',
    'category': 'Services/Timesheets',
    'summary': 'Automatically log timesheets for employee time off and public holidays.',
    'description': """
Bridge module to integrate leaves in timesheet
================================================

This module allows to automatically log timesheets when employees are
on leaves. Project and task can be configured company-wide.
    """,
    'depends': ['hr_timesheet', 'hr_holidays'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/project_task_views.xml',
        'security/ir.access.csv',

    ],
    'demo': [
        'data/holiday_timesheets_demo.xml',
    ],
    'auto_install': True,
    'post_init_hook': 'post_init',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
