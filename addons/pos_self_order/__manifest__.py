# -*- coding: utf-8 -*-
{
    'name': "POS Self Order",

    'summary': """
        Addon for the POS App that allows customers to view the menu on their smartphone.
        """,

    'category': 'Sales/Point Of Sale',

    'depends': ['pos_restaurant', 'http_routing'],
    'auto_install': ['pos_restaurant'],

    'demo': [
        'demo/pos_restaurant_demo.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/index.xml',
        'views/qr_code.xml',
        'views/custom_link_views.xml',
        'data/custom_link_data.xml',
        'views/res_config_settings_views.xml',
        'views/point_of_sale_dashboard.xml',
    ],
    'assets': {
        'pos_self_order.assets_self_order': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            ('include', 'web._assets_primary_variables'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'web/static/src/boot.js',
            'web/static/src/env.js',
            'web/static/src/session.js',
            'web/static/src/core/utils/transitions.scss',
            'web/static/src/core/**/*',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/lib/luxon/luxon.js',

            'web/static/src/views/fields/formatters.js',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',

            'pos_self_order/static/src/**/*',
            'point_of_sale/static/src/utils.js',
        ],
        'pos_self_order.assets_tests': [
            'web/static/lib/jquery/jquery.js',
            'web/static/lib/underscore/underscore.js',
            'web_tour/static/src/tour_pointer/**/*.js',
            'web_tour/static/src/tour_service/**/*.js',
            'pos_self_order/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
