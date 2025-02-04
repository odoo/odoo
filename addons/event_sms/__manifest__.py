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
        'security/ir.model.access.csv',
        'security/sms_security.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'event_sms/static/src/template_reference_field/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
