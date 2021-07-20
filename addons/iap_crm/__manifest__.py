# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "IAP / CRM",
    'summary': """Bridge between IAP and CRM""",
    'description': """Bridge between IAP and CRM""",
    'category': 'Hidden/Tools',
    'version': '1.1',
    'depends': [
        'crm',
        'iap_mail',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    'data': [
        'data/crm.iap.lead.industry.csv',
        'data/crm.iap.lead.role.csv',
        'data/crm.iap.lead.seniority.csv',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}
