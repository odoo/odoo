# -*- coding: utf-8 -*-
{
    "name": "POS Self Order",
    "summary": """
        Addon for the POS App that allows customers to view the menu on their smartphone.
        """,
    "category": "Sales/Point Of Sale",
    "depends": ["pos_restaurant", "http_routing"],
    "auto_install": ["pos_restaurant"],
    "demo": [
        "demo/pos_restaurant_demo.xml",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/index.xml",
        "views/qr_code.xml",
        "views/custom_link_views.xml",
        "data/init_access.xml",
        "views/res_config_settings_views.xml",
        "views/point_of_sale_dashboard.xml",
        "data/pos_restaurant_data.xml",
    ],
    "assets": {
        "pos_self_order.assets_self_order": [
            "web/static/lib/jquery/jquery.js",
            ("include", "web._assets_helpers"),
            ("include", "web._assets_backend_helpers"),
            ("include", "web._assets_primary_variables"),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_functions.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            ("include", "web._assets_bootstrap"),
            ("include", "web._assets_bootstrap_backend"),
            ('include', 'web._assets_core'),
            ("remove", "web/static/src/core/browser/router_service.js"),
            ("remove", "web/static/src/core/debug/**/*"),
            "web/static/src/views/fields/formatters.js",
            "web/static/src/libs/fontawesome/css/font-awesome.css",
            "web/static/lib/odoo_ui_icons/*",
            "pos_self_order/static/src/**/*",
            "point_of_sale/static/src/utils.js",
            # bus service
            'bus/static/src/services/bus_service.js',
            'bus/static/src/bus_parameters_service.js',
            'bus/static/src/multi_tab_service.js',
            'bus/static/src/workers/*',
        ],
        "pos_self_order.assets_tests": [
            "web/static/lib/jquery/jquery.js",
            "web_tour/static/src/tour_pointer/**/*.xml",
            "web_tour/static/src/tour_pointer/**/*.js",
            "web_tour/static/src/tour_service/**/*",
            "pos_self_order/static/tests/tours/**/*",
        ],
    },
    "license": "LGPL-3",
}
