# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright 2015 Eezee-It

{
    'name': 'Worldline SIPS',
    'version': '1.0',
    'author': 'Eezee-It',
    'category': 'Accounting',
    'description': """
Worldline SIPS Payment Acquirer for online payments

Works with Worldline keys version 2.0, contains implementation of
payments acquirer using Worldline SIPS.""",
    'depends': ['payment'],
    'data': [
        'views/sips.xml',
        'views/payment_acquirer.xml',
        'data/sips.xml',
    ],
    'installable': True,
}
