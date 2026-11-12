{
    "name": "Point of Sale Payments",
    "summary": "Base module for PoS payment methods",
    "category": "Sales/Point of Sale",
    "version": "0.1",
    "depends": ["bus"],
    "data": [
        "security/payment_method_security.xml",
        "security/ir.access.csv",
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pos_payment_method/static/src/pos_payment_provider_cards/*",
        ],
        "web.assets_unit_tests": [
            "pos_payment_method/static/src/payment_method.js",
            "pos_payment_method/static/tests/*",
        ],
        "point_of_sale.payment_terminals": [
            "pos_payment_method/static/src/payment_method.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
