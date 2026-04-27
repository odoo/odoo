# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Event Social",
    'category': 'Marketing/Social',
    'summary': "Publish on social account from Event",
    'description': """Publish on social account from Event.

This module allows you to schedule social posts from the event communication.""",
    'version': '1.0',
    'depends': ['event', 'social'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'event_social/static/src/template_reference_field/field_event_mail_template_reference.xml',
        ],
    },
    'license': 'OEEL-1',
}
