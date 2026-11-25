{
    "name": "PoS Worldline",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Integrate your PoS with a Worldline payment terminal",
    "depends": ["pos_payment_method"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_worldline/static/src/payment_method_worldline.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
