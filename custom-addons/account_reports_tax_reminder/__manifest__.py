# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Accounting Reports Tax Reminder',
    'summary': 'Add a notification when the tax report has been generated',
    'category': 'Accounting/Accounting',
    'description': """
Accounting Reports Tax Reminder
===============================
This module adds a notification when the tax report is ready to be sent
to the administration.
    """,
    'depends': ['account_reports'],
    'data': [
        'data/mail_activity_type_data.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
