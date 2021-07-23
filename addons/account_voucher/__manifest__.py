# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Sales & Purchases Receipts',
    'version' : '1.0',
    'summary': 'Manage your debts and credits thanks to simple sale/purchase receipts',
    'description': """
This module allows you recording sales and purchases receipts. Receipts are useful when the payment is done directly. Thanks to the receipts, no need to encode an invoice and a payment, the receipt is enough.
    """,
    'category': 'Accounting',
    'sequence': 20,
    'depends' : ['account'],
    'demo' : [],
    'data' : [
        'security/ir.model.access.csv',
        'views/account_voucher_views.xml',
        'security/account_voucher_security.xml',
        'data/account_voucher_data.xml',
    ],
    'auto_install': False,
    'installable': True,
    'license': 'LGPL-3',
}
