{
    "name": "PoS Adyen",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Integrate your PoS with an Adyen payment terminal",
    "depends": ["pos_payment_method"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_adyen/static/src/payment_method_adyen.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
