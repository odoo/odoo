# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'calendar_record',
    'version': '14.0.1.0.0',
    'summary': '--------------------',
    'sequence': 12,
    'description': """New Task: I need that you add a new security role to block that a user can see the all employees calendar. 
        User can only see his own calendar events.""",
    'category': '',
    'depends': [
            'base',
            'contacts',
            'calendar',
            'calendar_sms',
    ],
    'website': 'https://www.xyz.com',
    'data': [
        'security/calendar_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
