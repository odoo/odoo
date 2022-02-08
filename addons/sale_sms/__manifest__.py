# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale - SMS",
    'summary': "Ease SMS integration with sales capabilities",
    'description': "Ease SMS integration with sales capabilities",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['sale', 'sms'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
