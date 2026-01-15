# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "POS Self Order Pine Labs",
    "version": "1.0",
    "summary": "An addon for the Self Order App (KIOSK) that allows customers to pay using the Pine Labs POS Terminal.",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_pine_labs", "pos_self_order"],
    "auto_install": True,
    "assets": {
        "pos_self_order.assets": [
            "pos_self_order_pine_labs/static/src/**/*",
        ],
    },
    "author": "Odoo IN Pvt Ltd",
    "license": "LGPL-3",
}
