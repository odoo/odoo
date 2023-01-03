# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Vantiv Payment Services',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Credit card support for Point Of Sale',
    'description': """
Allow credit card POS payments
==============================

This module allows customers to pay for their orders with credit
cards. The transactions are processed by Vantiv (developed by Wells
Fargo Bank). A Vantiv merchant account is necessary. It allows the
following:

* Fast payment by just swiping a credit card while on the payment screen
* Combining of cash payments and credit card payments
* Cashback
* Supported cards: Visa, MasterCard, American Express, Discover
    """,
    'depends': ['web', 'barcodes', 'point_of_sale'],
    'data': [
        'data/pos_mercury_data.xml',
        'security/ir.model.access.csv',
        'views/pos_mercury_views.xml',
        'views/pos_mercury_transaction_templates.xml',
        'views/pos_config_setting_views.xml',
    ],
    'demo': [
        'data/pos_mercury_demo.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_mercury/static/src/js/pos_mercury.js',
            'pos_mercury/static/src/js/OrderReceipt.js',
            'pos_mercury/static/src/js/PaymentScreen.js',
            'pos_mercury/static/src/js/PaymentScreenPaymentLines.js',
            'pos_mercury/static/src/js/PaymentTransactionPopup.js',
            'pos_mercury/static/src/js/ProductScreen.js',
            'pos_mercury/static/src/css/pos_mercury.css',
            'pos_mercury/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
