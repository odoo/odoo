{
    "name": "POS SumUp",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Integrate your POS with a SumUp payment terminal",
    "data": [
        "views/pos_payment_method_views.xml",
    ],
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_sumup/static/src/**/*",
        ],
        "point_of_sale.payment_terminals": [
            "pos_sumup/static/src/app/utils/payment/payment_sumup.js",
            "pos_sumup/static/src/app/models/pos_payment.js",
        ],
        "web.assets_unit_tests": [
            "pos_sumup/static/tests/unit/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
