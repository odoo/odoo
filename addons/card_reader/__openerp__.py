{
    'name': 'card_reader',
    'version': '1.0',
    'category': '',
    'sequence': 6,
    'summary': 'Magnetic Code Nomenclatures Setup',
    'description': """

=======================

This module defines magnetic code nomenclatures whose rules identify e.g. visa, giftcards, ... .
It contains the following features:
- Magnetic code patterns to identify cards containing code for payment transaction
- Unlimited magnetic code patterns and definitions.
""",
    'author': 'Odoo SA',
    'depends': ['web', 'barcodes', 'point_of_sale'],
    'website': '',
    'data': [
        'data/card_reader_data.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/mercury_transaction.xml',
        'views/card_reader_config.xml',
    ],
    'qweb': [
        'static/src/xml/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
