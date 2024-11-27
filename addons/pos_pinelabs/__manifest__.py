{
    'name': 'POS Pine Labs',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Pine Labs payment terminal',
    'description': """
Allow Pine Labs POS payments
==============================

This module enables customers to pay for their orders using debit/credit cards and UPI.
Transactions are processed through Pine Labs POS, and a Pine Labs merchant account is required.
It allows the following:

* Experience quick payments by swiping, scanning, or tapping your credit/debit card or UPI QR code at the payment terminal.
* Supported cards: Visa, MasterCard, RuPay.
    """,
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_pinelabs/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
