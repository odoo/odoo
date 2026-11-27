{
    "name": "PoS Cashdro",
    "category": "Sales/Point of Sale",
    "summary": "Integrate your PoS with a Cashdro cash machine",
    "depends": ["pos_payment_method"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pos_payment_method_cashdro/static/src/backend/**/*",
        ],
        "point_of_sale.payment_terminals": [
            "pos_payment_method_cashdro/static/src/payment_method_cashdro.js",
        ],
        "web.assets_unit_tests": [
            "pos_payment_method_cashdro/static/tests/**/*",
            "pos_payment_method_cashdro/static/src/payment_method_cashdro.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
