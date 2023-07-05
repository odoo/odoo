# -*- coding: utf-8 -*-
{
    "name": "POS Self Order",
    "version": '1.0',
    "summary": """
        Addon for the POS App that allows customers to view the menu on their smartphone.
        """,
    "category": "Sales/Point Of Sale",
    "depends": ["point_of_sale", "http_routing"],
    "auto_install": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_self_order.index.xml",
        "views/pos_self_order.qr_code.xml",
        "views/custom_link_views.xml",
        "data/init_access.xml",
        "views/point_of_sale_dashboard.xml",
    ],
    "assets": {
        "pos_self_order.assets_global": [
            # web
            "web/static/lib/jquery/jquery.js",
            ("include", "web._assets_helpers"),
            ("include", "web._assets_backend_helpers"),
            ("include", "web._assets_primary_variables"),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_functions.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            ("include", "web._assets_bootstrap"),
            ("include", "web._assets_bootstrap_backend"),
            "web/static/src/boot.js",
            "web/static/src/env.js",
            "web/static/src/session.js",
            "web/static/src/core/utils/transitions.scss",
            "web/static/src/core/**/*",
            ('remove', 'web/static/src/core/emoji_picker/emoji_data.js'),
            ("remove", "web/static/src/core/browser/router_service.js"),
            ("remove", "web/static/src/core/debug/**/*"),
            "web/static/lib/owl/owl.js",
            "web/static/lib/owl/odoo_module.js",
            "web/static/lib/luxon/luxon.js",
            "web/static/src/views/fields/formatters.js",
            "web/static/src/libs/fontawesome/css/font-awesome.css",
            "web/static/lib/odoo_ui_icons/*",
            # point_of_sale
            "point_of_sale/static/src/utils.js",
            # bus service
            'bus/static/src/services/bus_service.js',
            'bus/static/src/bus_parameters_service.js',
            'bus/static/src/multi_tab_service.js',
            'bus/static/src/workers/*',
        ],
        "pos_self_order.assets_mobile": [
            ('include', 'pos_self_order.assets_global'),
            "pos_self_order/static/src/mobile/**/*",
        ],
    },
    "license": "LGPL-3",
}
