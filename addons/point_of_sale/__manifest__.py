# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale',
    'version': '1.0.1',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    'summary': 'User-friendly PoS interface for shops and restaurants',
    'depends': ['stock_account', 'barcodes', 'web_editor', 'digest'],
    'uninstall_hook': 'uninstall_hook',
    'data': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'data/default_barcode_patterns.xml',
        'data/digest_data.xml',
        'data/pos_note_data.xml',
        'wizard/pos_details.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_close_session_wizard.xml',
        'wizard/pos_daily_sales_reports.xml',
        'views/pos_assets_index.xml',
        'views/pos_assets_qunit.xml',
        'views/point_of_sale_report.xml',
        'views/point_of_sale_view.xml',
        'views/pos_note_view.xml',
        'views/pos_order_view.xml',
        'views/pos_category_view.xml',
        'views/pos_combo_view.xml',
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
        'views/pos_printer_view.xml',
        'views/pos_ticket_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'data/point_of_sale_demo.xml',
    ],
    'installable': True,
    'application': True,
    'website': 'https://www.odoo.com/app/point-of-sale-shop',
    'assets': {

        # In general, you DON'T NEED to declare new assets here, just put the
        # files in the proper directory. In rare cases, the order of scss files
        # matter and in that case you'll need to add it to the bundle in the
        # correct spot.
        #
        # Files in /static/src/backend will be loaded in the backend
        # Files in /static/src/app will be loaded in the PoS UI and unit tests
        # Files in /static/tests/tours will be loaded in the backend in test mode
        # Files in /static/tests/unit will be loaded in the qunit tests (/pos/ui/tests)

        # web assets
        'web.assets_backend': [
            'point_of_sale/static/src/scss/pos_dashboard.scss',
            'point_of_sale/static/src/backend/tours/point_of_sale.js',
            'point_of_sale/static/src/backend/debug_manager.js',
        ],
        'web.assets_tests': [
            'point_of_sale/static/tests/tours/**/*',
        ],

        # PoS assets

        'point_of_sale.base_app': [
            ("include", "web._assets_helpers"),
            ("include", "web._assets_backend_helpers"),
            ("include", "web._assets_primary_variables"),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_functions.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            ("include", "web._assets_bootstrap"),
            ("include", "web._assets_bootstrap_backend"),
            ('include', 'web._assets_core'),
            ("remove", "web/static/src/core/browser/router.js"),
            ("remove", "web/static/src/core/debug/**/*"),
            "web/static/src/libs/fontawesome/css/font-awesome.css",
            "web/static/src/views/fields/formatters.js",
            "web/static/lib/odoo_ui_icons/*",
            'web/static/src/legacy/scss/ui.scss',
            "point_of_sale/static/src/utils.js",
            'bus/static/src/services/bus_service.js',
            'bus/static/src/bus_parameters_service.js',
            'bus/static/src/multi_tab_service.js',
            'bus/static/src/workers/*',
        ],

        # Main PoS assets, they are loaded in the PoS UI and in the PoS unit tests
        'point_of_sale._assets_pos': [
            'web/static/src/scss/functions.scss',

            # JS boot
            'web/static/src/module_loader.js',
            # libs (should be loaded before framework)
            'point_of_sale/static/lib/**/*',
            'web/static/lib/luxon/luxon.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web_editor/static/lib/html2canvas.js',
            'web/static/lib/zxing-library/zxing-library.js',


            ('include', 'point_of_sale.base_app'),

            'web/static/src/core/colorlist/colorlist.scss',

            'web/static/src/webclient/icons.scss',

            # scss variables and utilities
            'point_of_sale/static/src/scss/pos_variables_extra.scss',
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/fonts/fonts.scss',

            ('remove', 'web/static/src/core/errors/error_handlers.js'), # error handling in PoS is different from the webclient
            ('remove', '/web/static/src/core/dialog/dialog.scss'),
            'web/static/src/core/currency.js',
            # barcode scanner
            'barcodes/static/src/barcode_service.js',
            'barcodes/static/src/js/barcode_parser.js',
            'barcodes_gs1_nomenclature/static/src/js/barcode_parser.js',
            'barcodes_gs1_nomenclature/static/src/js/barcode_service.js',
            'web/static/src/views/fields/parsers.js',
            'web/static/src/webclient/barcode/barcode_scanner.*',
            'web/static/src/webclient/barcode/ZXingBarcodeDetector.js',
            'web/static/src/webclient/barcode/crop_overlay.*',
            # report download utils
            'web/static/src/webclient/actions/reports/utils.js',
            # PoS files
            'point_of_sale/static/src/**/*',
            ('remove', 'point_of_sale/static/src/backend/**/*'),
            # main.js boots the pos app, it is only included in the prod bundle as tests mount the app themselves
            ('remove', 'point_of_sale/static/src/app/main.js'),
            # tour system FIXME: can this be added only in test mode? Are there any onboarding tours in PoS?
            "web_tour/static/src/tour_pointer/**/*",
            ("include", "point_of_sale.base_tests"),
            'web/static/src/legacy/js/libs/jquery.js',
            # account
            'account/static/src/helpers/*.js',

            "web/static/src/core/browser/router.js",
            "web/static/src/core/debug/**/*",
            'web/static/src/model/**/*',
            'web/static/src/views/**/*',
            'web/static/src/search/**/*',
            'web/static/src/webclient/actions/**/*',
            ('remove', 'web/static/src/webclient/actions/reports/layout_assets/**/*'),
            ('remove', 'web/static/src/webclient/actions/**/*css'),
            'web/static/src/webclient/company_service.js',
        ],
        'point_of_sale.base_tests': [
            "web/static/lib/jquery/jquery.js",
            "web/static/lib/hoot-dom/**/*",
            "web_tour/static/src/tour_pointer/**/*.xml",
            "web_tour/static/src/tour_pointer/**/*.js",
            "web_tour/static/src/tour_service/**/*",
        ],
        # Bundle that starts the pos, loaded on /pos/ui
        'point_of_sale.assets_prod': [
            ('include', 'point_of_sale._assets_pos'),
            'point_of_sale/static/src/app/main.js',
        ],
        # Bundle for the unit tests at /pos/ui/tests
        'point_of_sale.assets_qunit_tests': [
            ('include', 'point_of_sale._assets_pos'),
            "web/static/src/core/browser/router.js",
            "web/static/src/core/debug/**/*",
            # dependencies of web.tests_assets (in the web tests, these come from assets_backend)
            'web/static/tests/legacy/patch_translations.js',
            'web/static/lib/jquery/jquery.js',
            'web/static/src/legacy/js/**/*',
            ('remove', 'web/static/src/legacy/js/libs/**/*'),
            ('remove', 'web/static/src/legacy/js/public/**/*'),
            'web/static/src/search/**/*',
            'web/static/src/views/fields/field_tooltip.js',
            'web/static/src/views/fields/field.js',
            'web/static/src/views/onboarding_banner.js',
            'web/static/src/views/utils.js',
            'web/static/src/views/view_hook.js',
            'web/static/src/views/view_service.js',
            'web/static/src/views/view.js',
            'web/static/src/model/relational_model/utils.js',
            'web/static/src/webclient/actions/action_container.js',
            'web/static/src/webclient/actions/action_dialog.js',
            'web/static/src/webclient/actions/action_hook.js',
            'web/static/src/webclient/actions/action_service.js',
            'web/static/src/webclient/actions/reports/report_action.js',
            'web/static/src/webclient/actions/reports/report_hook.js',
            'web/static/src/webclient/menus/menu_service.js',
            'web/static/src/webclient/navbar/navbar.js',
            'web/static/src/webclient/webclient.js',
            'web/static/src/views/view_dialogs/form_view_dialog.js',
            'web/static/src/views/view_dialogs/select_create_dialog.js',
            # BEGIN copy of web.tests_assets. We don't 'include' it because other modules add their
            # own test helpers in this module that depend on files that they add in assets_backend
            'web/static/lib/qunit/qunit-2.9.1.css',
            'web/static/lib/qunit/qunit-2.9.1.js',
            'web/static/tests/legacy/legacy_tests/helpers/**/*',
            ('remove', 'web/static/tests/legacy/legacy_tests/helpers/test_utils_tests.js'),

            'web/static/lib/fullcalendar/core/index.global.js',
            'web/static/lib/fullcalendar/interaction/index.global.js',
            'web/static/lib/fullcalendar/daygrid/index.global.js',
            'web/static/lib/fullcalendar/timegrid/index.global.js',
            'web/static/lib/fullcalendar/list/index.global.js',
            'web/static/lib/fullcalendar/luxon3/index.global.js',

            'web/static/lib/zxing-library/zxing-library.js',

            'web/static/lib/ace/ace.js',
            'web/static/lib/ace/mode-python.js',
            'web/static/lib/ace/mode-xml.js',
            'web/static/lib/ace/mode-javascript.js',
            'web/static/lib/ace/mode-qweb.js',
            'web/static/lib/stacktracejs/stacktrace.js',
            ('include', "web.chartjs_lib"),

            # 'web/static/tests/legacy/main_tests.js',
            'web/static/tests/legacy/helpers/**/*.js',
            'web/static/tests/legacy/views/helpers.js',
            'web/static/tests/legacy/search/helpers.js',
            'web/static/tests/legacy/views/calendar/helpers.js',
            'web/static/tests/legacy/webclient/**/helpers.js',
            'web/static/tests/legacy/qunit.js',
            'web/static/tests/legacy/main.js',
            'web/static/tests/legacy/setup.js',

            ## END copy of web.tests_assets
            # pos unit tests
            'point_of_sale/static/tests/unit/**/*',
        ],
    },
    'license': 'LGPL-3',
}
