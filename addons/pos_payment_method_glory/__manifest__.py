{
    "name": "PoS Glory",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Integrate your PoS with a Glory cash machine",
    "depends": ["pos_payment_method"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_glory/static/src/payment_method_glory.js",
            "pos_payment_method_glory/static/src/utils/*.js",
            "pos_payment_method_glory/static/src/components/*",
        ],
        "web.assets_unit_tests": [
            "pos_payment_method_glory/static/src/payment_method_glory.js",
            "pos_payment_method_glory/static/tests/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
