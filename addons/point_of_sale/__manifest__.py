# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale',
    'version': '1.0.1',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    'summary': 'User-friendly PoS interface for shops and restaurants',
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
        'wizard/pos_session_check_product_wizard.xml',
        'views/pos_assets_common.xml',
        'views/pos_assets_index.xml',
        'views/pos_assets_qunit.xml',
        'views/point_of_sale_report.xml',
        'views/point_of_sale_view.xml',
        'views/pos_order_view.xml',
        'views/pos_category_view.xml',
        'views/product_view.xml',
        'views/account_journal_view.xml',
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
        'views/res_config_settings_views.xml',
        'views/pos_ticket_view.xml',
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
        ],
        'web.assets_tests': [
            'point_of_sale/static/tests/tours/**/*',
        ],
        'web.assets_qweb': [
            'point_of_sale/static/src/xml/**/*.xml',
        ],

        ####################################################
        ## Exclusive POS Assets 1: For running the POS UI ##
        ####################################################

        'point_of_sale.pos_assets_backend_style': [
            "web/static/src/core/ui/**/*.scss",
        ],
        # TODO: We need to control this asset bundle.
        # We can reduce the size of loaded assets in POS UI by selectively
        # loading the `web` assets. We should only include what POS needs.
        'point_of_sale.pos_assets_backend': [
            ('include', 'web.assets_backend'),
            ('remove', 'web/static/src/core/errors/error_handlers.js'),
            ('remove', 'web/static/src/legacy/legacy_rpc_error_handler.js'),
        ],
        # This bundle includes the main pos assets.
        'point_of_sale.assets': [
            'point_of_sale/static/src/scss/pos_variables_extra.scss',
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            ('include', 'web._assets_primary_variables'),
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/fonts/fonts.scss',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/daterangepicker/daterangepicker.css',
            'point_of_sale/static/src/scss/pos.scss',
            'point_of_sale/static/src/css/pos_receipts.css',
            'point_of_sale/static/src/css/popups/product_info_popup.css',
            'point_of_sale/static/src/css/popups/common.css',
            'point_of_sale/static/src/css/popups/cash_opening_popup.css',
            'point_of_sale/static/src/css/popups/closing_pos_popup.css',
            'point_of_sale/static/src/css/popups/money_details_popup.css',
            'web/static/src/legacy/scss/fontawesome_overridden.scss',

            # Here includes the lib and POS UI assets.
            'point_of_sale/static/lib/**/*.js',
            'web_editor/static/lib/html2canvas.js',
            'point_of_sale/static/src/js/**/*.js',
            'web/static/lib/zxing-library/zxing-library.js',
        ],
        # This bundle contains the code responsible for starting the POS UI.
        # It is practically the entry point.
        'point_of_sale.assets_backend_prod_only': [
            'point_of_sale/static/src/entry/chrome_adapter.js',
            'point_of_sale/static/src/entry/main.js',
            'web/static/src/start.js',
            'web/static/src/legacy/legacy_setup.js',
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
            'web/static/src/libs/bootstrap/pre_variables.scss',
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
