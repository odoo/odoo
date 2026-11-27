{
    "name": "PoS Mollie",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Integrate your PoS with a Mollie payment terminal",
    "depends": ["pos_payment_method", "payment_mollie"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_mollie/static/src/payment_method_mollie.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
