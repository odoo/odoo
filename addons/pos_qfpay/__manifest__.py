{
    "name": "POS QFPay",
    "version": "1.1",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Integrate your POS with the QFPay terminal in Hong Kong",
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
            "pos_qfpay/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_qfpay/static/src/app/qfpay.js",
            "pos_qfpay/static/tests/tours/**/*",
        ],
    },
}
