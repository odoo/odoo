# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS on Events',
    'version': '1.0',
    'category': 'Marketing',
    'description': """Schedule SMS in event management""",
    'depends': ['event', 'sms'],
    'data': [
        'data/sms_data.xml',
        'views/event_views.xml',
        'views/event_mail_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True
}
