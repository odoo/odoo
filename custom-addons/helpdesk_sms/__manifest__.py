# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Helpdesk - SMS",
    'summary': 'Send text messages when ticket stage move',
    'description': "Send text messages when ticket stage move",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['helpdesk', 'sms'],
    'data': [
        'views/helpdesk_stage_views.xml',
        'views/helpdesk_sms_views.xml',
        'security/ir.model.access.csv',
        'security/helpdesk_sms_security.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
