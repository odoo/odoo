{
    "name": "PoS Mercado Pago",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Integrate your PoS with a Mercado Pago payment terminal",
    "depends": ["pos_payment_method"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_mercado_pago/static/src/payment_method_mercado_pago.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
