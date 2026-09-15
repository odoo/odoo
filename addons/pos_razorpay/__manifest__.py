{
    "name": "POS Razorpay",
    "version": "1.1",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Integrate your POS with a Razorpay payment terminal",
    "description": """
Allow Razorpay POS payments
==============================

This module allows customers to pay for their orders with debit/credit
cards and UPI. The transactions are processed by Razorpay POS. A Razorpay merchant account is necessary. It allows the
following:

* Fast payment by just swiping/scanning a credit/debit card or a QR code while on the payment screen
* Supported cards: Visa, MasterCard, Rupay, UPI
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "integration",
    ],
    "data": [
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_razorpay/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_razorpay/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_razorpay/static/tests/unit/data/**/*",
        ],
    },
}
