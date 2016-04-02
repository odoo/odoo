# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mercury Payment Services',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Credit card support for Point Of Sale',
    'description': """
Allow credit card POS payments
==============================

This module allows customers to pay for their orders with credit
cards. The transactions are processed by Mercury (developed by Wells
Fargo Bank). A Mercury merchant account is necessary. It allows the
following:

* Fast payment by just swiping a credit card while on the payment screen
* Combining of cash payments and credit card payments
* Cashback
* Supported cards: Visa, MasterCard, American Express, Discover
    """,
    'depends': ['web', 'barcodes', 'point_of_sale'],
    'website': '',
    'data': [
        'data/pos_mercury_data.xml',
        'security/ir.model.access.csv',
        'views/pos_mercury_templates.xml',
        'views/pos_mercury_views.xml',
        'views/pos_mercury_transaction_templates.xml',
    ],
    'demo': [
        'data/pos_mercury_demo.xml',
    ],
    'qweb': [
        'static/src/xml/pos_mercury.xml',
    ],
    'installable': True,
    'auto_install': False,
}
