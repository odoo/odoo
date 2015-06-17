{
    'name': 'Card Reader',
    'version': '1.0',
    'category': '',
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
    'author': 'Odoo SA',
    'depends': ['web', 'barcodes', 'point_of_sale'],
    'website': '',
    'data': [
        'data/card_reader_data.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/mercury_transactions.xml',
        'views/card_reader_config.xml',
    ],
    'demo': [
        'data/card_reader_demo.xml',
    ],
    'qweb': [
        'static/src/xml/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
