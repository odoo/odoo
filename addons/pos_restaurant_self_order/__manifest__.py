# -*- coding: utf-8 -*-
{
    "name": "POS Restaurant Self Order",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_restaurant", "pos_self_order"],
    "auto_install": ["pos_restaurant"],
    "demo": [
        "demo/pos_restaurant_demo.xml",
    ],
    "data": [
        "data/init_access.xml",
        "data/pos_restaurant_data.xml",
        "views/res_config_settings_views.xml",
        "views/pos_self_order.index.xml",
    ],
    "assets": {
         "pos_self_order.assets_mobile": [
            "pos_restaurant_self_order/static/src/mobile/**/*",
        ],
        "pos_restaurant_self_order.assets_tests": [
            "web/static/lib/jquery/jquery.js",
            "web_tour/static/src/tour_pointer/**/*.xml",
            "web_tour/static/src/tour_pointer/**/*.js",
            "web_tour/static/src/tour_service/**/*",
            "pos_restaurant_self_order/static/tests/tours/**/*",
        ],
    },
    "license": "LGPL-3",
}
