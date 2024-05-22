# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS on Events',
    'version': '1.0',
    'category': 'Marketing/Events',
    'description': """Schedule SMS in event management""",
    'depends': ['event', 'sms'],
    'data': [
        'data/sms_data.xml',
        'views/event_views.xml',
        'views/event_mail_views.xml',
        'security/ir.model.access.csv',
        'security/sms_security.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
