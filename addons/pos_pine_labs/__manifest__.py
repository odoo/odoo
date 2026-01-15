{
    'name': 'POS Pine Labs',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with Pine Labs payment terminals',
    'description': """
Allow Pine Labs POS payments
==============================

This module is available only for companies that use INR currency.
It enables customers to pay for their orders using debit/credit cards and UPI through Pine Labs POS terminals.
A Pine Labs merchant account is required to process transactions.
Features include:

* Quick payments by swiping, scanning, or tapping your credit/debit card or UPI QR code at the payment terminal.
* Supported cards: Visa, MasterCard, RuPay.
    """,
    'data': [
        'views/pos_payment_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_pine_labs/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_pine_labs/static/tests/unit/data/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
