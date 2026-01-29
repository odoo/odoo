# -*- coding: utf-8 -*-
{
    "name": "POS Self Order Sale",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_sale", "pos_self_order"],
    "auto_install": True,
    "data": [
        "views/res_config_settings_views.xml",
        "data/kiosk_sale_team.xml",
    ],
    "assets": {
        # Assets
        "pos_self_order.assets": [
            "pos_self_order_sale/static/src/app/**/**",
        ],
    },
    "license": "LGPL-3",
}
