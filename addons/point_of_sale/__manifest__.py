# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale',
    'version': '1.0.1',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    'summary': 'User-friendly PoS interface for shops and restaurants',
    'description': "",
    'depends': ['stock_account', 'barcodes', 'web_editor', 'digest'],
    'data': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'data/default_barcode_patterns.xml',
        'data/digest_data.xml',
        'wizard/pos_box.xml',
        'wizard/pos_details.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_close_session_wizard.xml',
        'views/pos_assets_index.xml',
        'views/pos_assets_qunit.xml',
        'views/point_of_sale_report.xml',
        'views/point_of_sale_view.xml',
        'views/pos_order_view.xml',
        'views/pos_category_view.xml',
        'views/product_view.xml',
        'views/account_journal_view.xml',
        'views/res_config_settings_views.xml',
        'views/pos_payment_method_views.xml',
        'views/pos_payment_views.xml',
        'views/pos_config_view.xml',
        'views/pos_bill_view.xml',
        'views/pos_session_view.xml',
        'views/point_of_sale_sequence.xml',
        'data/point_of_sale_data.xml',
        'views/pos_order_report_view.xml',
        'views/account_statement_view.xml',
        'views/digest_views.xml',
        'views/res_partner_view.xml',
        'views/report_userlabel.xml',
        'views/report_saledetails.xml',
        'views/point_of_sale_dashboard.xml',
        'views/report_invoice.xml',
    ],
    'demo': [
        'data/point_of_sale_demo.xml',
    ],
    'installable': True,
    'application': True,
    'website': 'https://www.odoo.com/app/point-of-sale-shop',
    'assets': {

        ## In general, you DON'T NEED to declare new assets here, just put the files in the proper directory.
        ## NOTABLE EXCEPTION: List the new .css files in the `point_of_sale.assets` bundle taking into consideration
        ##   the order of the .css files.
        ##
        ## 1. When defining new component, put the .js files in `point_of_sale/static/src/js/`
        ##    and the corresponding .xml files in `point_of_sale/static/src/xml/`
        ##    * POS is setup to automatically include the .xml files in `web.assets_qweb` and the `.js` files
        ##    * in `point_of_sale.assets`.
        ## 2. When adding new tour tests, put the .js files in `point_of_sale/static/tests/tours/`.
        ## 3. When adding new qunit tests, put the .js files in `point_of_sale/static/tests/unit/`.
        ##
        ## If your use case doesn't fit anything above, you might need to properly understand each "asset bundle"
        ## defined here and check how they are used in the following "index templates":
        ##      1. point_of_sale.index
        ##          ->  This is the POS UI, accessible by opening a session.
        ##      2. point_of_sale.qunit_suite
        ##          ->  This is the unit test, accessible by clicking the "Run Point of Sale JS Tests" button
        ##              in the "debug" button from the backend interface.

        #####################################
        ## Augmentation of existing assets ##
        #####################################

        'web.assets_backend': [
            'point_of_sale/static/src/scss/pos_dashboard.scss',
            'point_of_sale/static/src/backend/tours/point_of_sale.js',
            'point_of_sale/static/src/backend/debug_manager.js',
            'point_of_sale/static/src/backend/web_overrides/pos_config_form.js',
        ],
        'web.assets_tests': [
            'point_of_sale/static/tests/tours/**/*',
        ],

        ####################################################
        ## Exclusive POS Assets 1: For running the POS UI ##
        ####################################################

        'point_of_sale.assets_qweb': [
            'web/static/src/webclient/loading_indicator/loading_indicator.xml',
            'point_of_sale/static/src/xml/**/*.xml',
        ],
        'point_of_sale.required_style_assets': [
            "web/static/src/core/ui/**/*.scss",
        ],
        # This bundle contains the necessary modules from web needed to open the pos ui.
        # Extract only js files in this asset bundle.
        'point_of_sale.required_assets': [
            ('include', 'web.assets_common'),
            ('remove', 'web/static/src/legacy/js/core/menu.js'),
            # lib
            'web/static/lib/py.js/lib/py.js',
            'web/static/lib/py.js/lib/py_extras.js',
            'web/static/lib/luxon/luxon.js',
            # modules
            'bus/static/src/js/longpolling_bus.js',
            'bus/static/src/js/crosstab_bus.js',
            'bus/static/src/js/services/bus_service.js',
            'barcodes/static/src/js/barcode_events.js',
            'barcodes/static/src/js/barcode_parser.js',
            'web_tour/static/src/js/tour_service.js',
            'web/static/src/core/assets.js',
            'web/static/src/core/browser/browser.js',
            'web/static/src/core/browser/feature_detection.js',
            'web/static/src/core/context.js',
            'web/static/src/core/dialog/dialog.js',
            'web/static/src/core/errors/error_dialogs.js',
            'web/static/src/core/hotkeys/hotkey_hook.js',
            'web/static/src/core/l10n/localization.js',
            'web/static/src/core/l10n/translation.js',
            'web/static/src/core/network/rpc_service.js',
            'web/static/src/core/py_js/py_builtin.js',
            'web/static/src/core/py_js/py_date.js',
            'web/static/src/core/py_js/py_interpreter.js',
            'web/static/src/core/py_js/py_parser.js',
            'web/static/src/core/py_js/py_tokenizer.js',
            'web/static/src/core/py_js/py_utils.js',
            'web/static/src/core/py_js/py.js',
            'web/static/src/core/registry.js',
            'web/static/src/core/transition.js',
            'web/static/src/core/ui/block_ui.js',
            'web/static/src/core/ui/ui_service.js',
            'web/static/src/core/ui/ui_service.js',
            'web/static/src/core/utils/functions.js',
            'web/static/src/core/utils/hooks.js',
            'web/static/src/core/utils/render.js',
            'web/static/src/core/utils/strings.js',
            'web/static/src/core/utils/timing.js',
            'web/static/src/env.js',
            'web/static/src/legacy/backend_utils.js',
            'web/static/src/legacy/js/control_panel/search_utils.js',
            'web/static/src/legacy/js/core/domain.js',
            'web/static/src/legacy/js/core/misc.js',
            'web/static/src/legacy/js/core/py_utils.js',
            'web/static/src/legacy/js/env.js',
            'web/static/src/legacy/js/fields/field_utils.js',
            'web/static/src/legacy/js/model.js',
            'web/static/src/legacy/js/owl_compatibility.js',
            'web/static/src/legacy/js/services/data_manager.js',
            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/views/action_model.js',
            'web/static/src/legacy/js/views/view_utils.js',
            'web/static/src/legacy/root_widget.js',
            'web/static/src/webclient/actions/action_service.js',
            'web/static/src/webclient/loading_indicator/loading_indicator.js',
            # Starting here, the following are dependencies of action_service.
            'web/static/src/search/layout.js',
            'web/static/src/webclient/actions/scrolling.js',
            'web/static/src/core/position_hook.js',
            'web/static/src/core/user_service.js',
            'web/static/src/core/debug/debug_context.js',
            'web/static/src/core/network/download.js',
            'web/static/src/core/utils/concurrency.js',
            'web/static/src/legacy/utils.js',
            'web/static/src/views/view.js',
            'web/static/src/webclient/actions/action_dialog.js',
            'web/static/src/webclient/actions/action_hook.js',
            'web/static/src/core/utils/objects.js',
            'web/static/src/search/with_search/with_search.js',
            'web/static/src/views/helpers/view_hook.js',
            'web/static/src/core/debug/debug_menu.js',
            'web/static/src/core/utils/scrolling.js',
            'web/static/src/search/search_model.js',
            'web/static/src/search/control_panel/control_panel.js',
            'web/static/src/search/search_panel/search_panel.js',
            'web/static/src/core/dropdown/dropdown.js',
            'web/static/src/core/dropdown/dropdown_item.js',
            'web/static/src/core/debug/debug_menu_basic.js',
            'web/static/src/core/commands/command_hook.js',
            'web/static/src/core/domain.js',
            'web/static/src/core/utils/arrays.js',
            'web/static/src/search/search_arch_parser.js',
            'web/static/src/search/utils/dates.js',
            'web/static/src/search/utils/misc.js',
            'web/static/src/core/pager/pager.js',
            'web/static/src/search/comparison_menu/comparison_menu.js',
            'web/static/src/search/favorite_menu/favorite_menu.js',
            'web/static/src/search/filter_menu/filter_menu.js',
            'web/static/src/search/group_by_menu/group_by_menu.js',
            'web/static/src/search/search_bar/search_bar.js',
            'web/static/src/core/dropdown/dropdown_navigation_hook.js',
            'web/static/src/core/utils/xml.js',
            'web/static/src/core/l10n/dates.js',
            'web/static/src/core/confirmation_dialog/confirmation_dialog.js',
            'web/static/src/search/filter_menu/custom_filter_item.js',
            'web/static/src/search/group_by_menu/custom_group_by_item.js',
            'web/static/src/core/utils/search.js',
            'web/static/src/core/datepicker/datepicker.js',
            # effect_service
            'web/static/src/core/effects/effect_service.js',
            'web/static/src/core/effects/effect_container.js',
            'web/static/src/core/effects/rainbow_man.js',
            # localization_service
            'web/static/src/core/l10n/localization_service.js',
            # notification_service
            'web/static/src/core/notifications/notification_service.js',
            'web/static/src/core/notifications/notification_container.js',
            'web/static/src/core/notifications/notification.js',
            # router_service
            'web/static/src/core/browser/router_service.js',
            'web/static/src/core/utils/urls.js',
            # title_service
            'web/static/src/core/browser/title_service.js',
            # company_service
            'web/static/src/webclient/company_service.js',
            'web/static/src/core/browser/cookie_service.js',
        ],
        # This bundle includes the main pos assets.
        'point_of_sale.assets': [
            'web/static/fonts/fonts.scss',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/daterangepicker/daterangepicker.css',
            'point_of_sale/static/src/css/pos.css',
            'point_of_sale/static/src/css/pos_receipts.css',
            'point_of_sale/static/src/css/popups/product_info_popup.css',
            'point_of_sale/static/src/css/popups/common.css',
            'point_of_sale/static/src/css/popups/cash_opening_popup.css',
            'point_of_sale/static/src/css/popups/closing_pos_popup.css',
            'point_of_sale/static/src/css/popups/money_details_popup.css',
            'web/static/src/legacy/scss/fontawesome_overridden.scss',

            # Here includes the lib and POS UI assets.
            'point_of_sale/static/lib/**/*.js',
            'point_of_sale/static/src/js/**/*.js',
        ],
        # This bundle contains the code responsible for starting the POS UI.
        # It is practically the entry point.
        'point_of_sale.entry': [
            'point_of_sale/static/src/entry/chrome_adapter.js',
            'point_of_sale/static/src/entry/main.js',
            'web/static/src/start.js',
            'point_of_sale/static/src/entry/custom_legacy_setup.js',
        ],

        #########################################################
        ## Exclusive POS Assets 2: For running the QUnit tests ##
        #########################################################

        # This bundle includes the helper assets for the unit testing.
        'point_of_sale.tests_assets': [
            'web/static/lib/qunit/qunit-2.9.1.css',
            'web/static/lib/qunit/qunit-2.9.1.js',
            'web/static/tests/legacy/helpers/**/*',
            ('remove', 'web/static/tests/legacy/helpers/test_utils_tests.js'),

            'web/static/tests/legacy/legacy_setup.js',

            'web/static/tests/helpers/**/*.js',
            'web/static/tests/qunit.js',
            'web/static/tests/main.js',
            'web/static/tests/setup.js',

            # These 2 lines below are taken from web.assets_frontend
            # They're required for the web.frontend_legacy to work properly
            # It is expected to add other lines coming from the web.assets_frontend
            # if we need to add more and more legacy stuff that would require other scss or js.
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web.frontend_legacy'),
        ],
        # This bundle includes the unit tests.
        'point_of_sale.qunit_suite_tests': [
            'point_of_sale/static/tests/unit/**/*',
        ],
    },
    'license': 'LGPL-3',
}
