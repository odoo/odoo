# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheet when on Leaves',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Schedule timesheet when on leaves',
    'description': """
Bridge module to integrate holidays in timesheet
================================================

This module allows to automatically log timesheets when employees are
on leaves. Project and task can be configured company-wide.
    """,
    'depends': ['hr_timesheet', 'hr_holidays'],
    'data': [
        'views/res_config_views.xml',
        'views/hr_holidays_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
}
