# -*- coding: utf-8 -*-
{
    "name": "POS Self Order",
    'version': '1.0.1',
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
        "views/pos_self_order_mobile.index.xml",
        "views/pos_self_order_kiosk.index.xml",
        "views/qr_code.xml",
        "views/pos_config_view.xml",
        "views/custom_link_views.xml",
        "data/init_access.xml",
        "views/res_config_settings_views.xml",
        "views/point_of_sale_dashboard.xml",
        "data/pos_restaurant_data.xml",
    ],
    "assets": {
        # Assets
        'web.assets_backend': [
            "pos_self_order/static/src/upgrade_selection_field.js",
        ],
        "pos_self_order.assets_common": [
            "pos_self_order/static/src/kiosk/bootstrap_overridden.scss",
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
            'web/static/src/legacy/scss/ui.scss',
            "point_of_sale/static/src/utils.js",
            'bus/static/src/services/bus_service.js',
            'bus/static/src/bus_parameters_service.js',
            'bus/static/src/multi_tab_service.js',
            'bus/static/src/workers/*',
            "pos_self_order/static/src/common/**/*",
        ],
        "pos_self_order.assets_mobile": [
            ('include', 'pos_self_order.assets_common'),
            "pos_self_order/static/src/mobile/**/*",
        ],
        "pos_self_order.assets_kiosk": [
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
            'web/static/lib/bootstrap/js/dist/base-component.js',
            "web/static/lib/bootstrap/js/dist/carousel.js",
            ('include', 'pos_self_order.assets_common'),
            "pos_self_order/static/src/kiosk/**/*",
        ],
        # Assets tests
        "pos_self_order.assets_common_tests": [
            "web/static/lib/jquery/jquery.js",
            "web_tour/static/src/tour_pointer/**/*.xml",
            "web_tour/static/src/tour_pointer/**/*.js",
            "web_tour/static/src/tour_service/**/*",
            "pos_self_order/static/tests/utils/**/*",
        ],
        "pos_self_order.assets_mobile_tests": [
            ('include', 'pos_self_order.assets_common_tests'),
            "pos_self_order/static/tests/tours/mobile/**/*",
        ],
        "pos_self_order.assets_kiosk_tests": [
            ('include', 'pos_self_order.assets_common_tests'),
            "pos_self_order/static/tests/tours/kiosk/**/*",
        ],
    },
    "license": "LGPL-3",
}
