# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Presence Control',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Control Employees Presence
==========================

Based on:
    * The IP Address
    * The User's Session
    * The Sent Emails

Allows to contact directly the employee in case of unjustified absence.
    """,
    'depends': ['hr', 'hr_holidays', 'sms'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'data/ir_actions_server.xml',
        'data/mail_data.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
