# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "POS Self Order Viva.com",
    "summary": "Addon for the Self Order App that allows customers to pay by Viva.com POS Terminal.",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_viva_com", "pos_self_order"],
    "auto_install": True,
    "assets": {
        "pos_self_order.assets_tests": [
            "pos_self_order_viva_com/static/tests/tours/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
