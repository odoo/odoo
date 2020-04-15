# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Time Off - Calendar',
    'version': '1.5',
    'category': 'Human Resources/Time Off',
    'summary': '',
    'description': """""",
    'depends': ['hr_holidays', 'calendar'],
    'data': [
        'report/hr_leave_report_calendar_views.xml',
        'security/ir.model.access.csv',
        'security/hr_holidays_calendar_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
