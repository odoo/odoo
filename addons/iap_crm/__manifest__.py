# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "IAP / CRM",
    'summary': """Bridge between IAP and CRM""",
    'description': """Bridge between IAP and CRM""",
    'category': 'Hidden/Tools',
    'version': '1.0',
    'depends': [
        'crm',
        'iap_mail',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'data': [
    ],
    'license': 'LGPL-3',
}
