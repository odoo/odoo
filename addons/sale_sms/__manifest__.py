# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale - SMS",
    'summary': "Ease SMS integration with sales capabilities",
    'description': "Ease SMS integration with sales capabilities",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['sale', 'sms'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
