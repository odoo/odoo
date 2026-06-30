# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Calendar - SMS",
    'version': "1.1",
    'summary': 'Send text messages as event reminders',
    'description': "Send text messages as event reminders",
    'category': 'Productivity/Calendar',
    'depends': ['calendar', 'sms'],
    'data': [
        'data/sms_data.xml',
        'views/calendar_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
