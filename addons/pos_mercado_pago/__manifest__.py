{
    "name": "POS Mercado Pago",
    "version": "1.1",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Integrate your POS with the Mercado Pago Smart Point terminal",
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
            "pos_mercado_pago/static/**/*",
        ],
    },
}
