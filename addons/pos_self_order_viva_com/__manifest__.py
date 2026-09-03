{
    "name": "POS Self Order Viva.com",
    "summary": "Addon for the Self Order App that allows customers to pay with Viva.com terminals.",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_viva_com", "pos_self_order"],
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "assets": {
        "pos_self_order.assets": [
            "pos_self_order_viva_com/static/src/**/*.js"
        ]
    }
}
