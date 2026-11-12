{
    "name": "PoS Stripe",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Integrate your PoS with a Stripe payment terminal",
    "depends": ["pos_payment_method", "payment_stripe"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_stripe/static/src/payment_method_stripe.js",
        ],
        "web.assets_unit_tests": [
            "pos_payment_method_stripe/static/src/payment_method_stripe.js",
            "pos_payment_method_stripe/static/tests/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
