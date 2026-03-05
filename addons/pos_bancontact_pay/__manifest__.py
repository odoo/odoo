{
    "name": "POS Bancontact Pay",
    "category": "Sales/Point of Sale",
    "sequence": 100,
    "summary": "Accept Bancontact Pay QR code payments (Payconiq / Wero) in POS.",
    "data": ["views/pos_payment_method_views.xml"],
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_bancontact_pay/static/src/**/*",
        ],
        'point_of_sale.payment_terminals': [
            'pos_bancontact_pay/static/src/app/payment_bancontact.js',
            'pos_bancontact_pay/static/src/app/pos_payment_method.js',
            'pos_bancontact_pay/static/src/app/pos_payment.js',
        ],
        "web.assets_tests": [
            "pos_bancontact_pay/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_bancontact_pay/static/tests/unit/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
