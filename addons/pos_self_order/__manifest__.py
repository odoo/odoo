# -*- coding: utf-8 -*-
{
    "name": "POS Self Order",
    'version': '1.0',
    "summary": "Addon for the POS App that allows customers to view the menu on their smartphone.",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_restaurant", "http_routing", "link_tracker"],
    "auto_install": ["pos_restaurant"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "data/preset_data.xml",
        "views/pos_self_order.index.xml",
        "views/qr_code.xml",
        "views/pos_category_views.xml",
        "views/pos_config_view.xml",
        "views/pos_session_view.xml",
        "views/custom_link_views.xml",
        "views/pos_restaurant_views.xml",
        "views/product_views.xml",
        "views/pos_preset_view.xml",
        "data/init_access.xml",
        "views/res_config_settings_views.xml",
        "views/point_of_sale_dashboard.xml",
    ],
    "demo": [
        "data/kiosk_demo_data.xml",
    ],
    "assets": {
        # Assets
        'web.assets_unit_tests_setup': [
            ('include', 'pos_self_order.assets'),
            ('remove', 'pos_self_order/static/src/app/root.js'),

            # Remove the conflicting "printer" service to avoid duplicate registration during tests
            ('remove', 'pos_self_order/static/src/app/services/printer_service.js'),

            # Remove CSS files since we're not testing the UI with hoot in PoS self order
            # CSS files make html_editor tests fail
            ('remove', 'pos_self_order/static/src/**/*.scss'),
            ('remove', 'point_of_sale/static/src/css/pos_receipts.css'),

            # Re-include debug and router files that were removed in point_of_sale.base_app
            # but are required for running unit tests
            'web/static/src/core/debug/**/*',
            'web/static/src/core/browser/router.js',
        ],
        'web.assets_unit_tests': [
            'pos_self_order/static/tests/unit/**/*',
        ],
        'point_of_sale._assets_pos': [
            'pos_self_order/static/src/backend/qr_order_button/*',
            'pos_self_order/static/src/overrides/**/*',
        ],
        'web.assets_backend': [
            "pos_self_order/static/src/upgrade_selection_field.js",
            'pos_self_order/static/src/backend/qr_order_button/*',
        ],
        "pos_self_order.assets": [
            "pos_self_order/static/src/app/primary_variables.scss",
            "pos_self_order/static/src/app/bootstrap_overridden.scss",
            ("include", "point_of_sale.base_app"),
            'web/static/src/core/currency.js',
            'barcodes/static/src/barcode_service.js',
            'point_of_sale/static/src/utils.js',
            'point_of_sale/static/src/proxy_trap.js',
            'point_of_sale/static/src/lazy_getter.js',
            'web/static/lib/bootstrap/js/dist/util/index.js',
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
            'web/static/lib/bootstrap/js/dist/util/config.js',
            'web/static/lib/bootstrap/js/dist/util/swipe.js',
            'web/static/lib/bootstrap/js/dist/base-component.js',
            "web/static/lib/bootstrap/js/dist/carousel.js",
            'web/static/lib/bootstrap/js/dist/scrollspy.js',
            'html_editor/static/src/scss/base_style.scss',
            'html_editor/static/src/scss/html_editor.common.scss',
            "point_of_sale/static/src/app/components/numpad/*",
            "point_of_sale/static/src/app/components/product_card/*",
            "point_of_sale/static/src/app/components/order_display/*",
            "point_of_sale/static/src/app/components/orderline/*",
            "point_of_sale/static/src/app/components/centered_icon/*",
            "point_of_sale/static/src/app/components/epos_templates.xml",
            "point_of_sale/static/src/css/pos_receipts.css",
            "point_of_sale/static/src/app/screens/receipt_screen/receipt/**/*",
            "pos_self_order/static/src/overrides/components/receipt_header/*",
            "point_of_sale/static/src/app/utils/printer/*",
            "point_of_sale/static/src/app/services/printer_service.js",
            'point_of_sale/static/src/app/utils/html-to-image.js',
            'point_of_sale/static/src/app/utils/use_timed_press.js',
            "point_of_sale/static/src/app/services/render_service.js",
            "pos_self_order/static/src/app/**/*",
            "web/static/src/core/utils/render.js",
            "pos_self_order/static/src/app/store/order_change_receipt_template.xml",
            "account/static/src/helpers/*.js",
            'web/static/src/model/relational_model/operation.js',
            "web/static/src/views/fields/parsers.js",

            # Related models from point_of_sale
            "point_of_sale/static/src/app/models/data_service_options.js",
            "point_of_sale/static/src/app/models/utils/indexed_db.js",
            "point_of_sale/static/src/app/models/related_models/**/*",
            "point_of_sale/static/src/app/services/data_service.js",
            "point_of_sale/static/src/app/models/**/*",
            "pos_restaurant/static/src/app/models/restaurant_table.js",
            "point_of_sale/static/src/app/utils/numbers.js",
            "point_of_sale/static/src/app/utils/pretty_console_log.js",
            "point_of_sale/static/src/app/utils/devices_identifier_sequence.js",
            "point_of_sale/static/src/app/hooks/hooks.js",
            "point_of_sale/static/src/app/utils/debug-formatter.js",
            "point_of_sale/static/src/app/store/order_change_receipt_template.xml",
        ],
        # Assets tests
        "pos_self_order.assets_tests": [
            ("include", "point_of_sale.base_tests"),
            "pos_self_order/static/tests/tours/**/*",
            "point_of_sale/static/tests/generic_helpers/numpad_util.js",
            "point_of_sale/static/tests/generic_helpers/dialog_util.js",
            "point_of_sale/static/tests/generic_helpers/utils.js",
        ],
        'web.assets_tests': [
            'pos_self_order/static/tests/pos/**/*',
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
