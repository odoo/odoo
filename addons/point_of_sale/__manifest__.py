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
        'wizard/pos_details.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_close_session_wizard.xml',
        'wizard/pos_daily_sales_reports.xml',
        'views/pos_assets_index.xml',
        'views/pos_assets_qunit.xml',
        'views/point_of_sale_report.xml',
        'views/point_of_sale_view.xml',
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

        # Main PoS assets, they are loaded in the PoS UI and in the PoS unit tests
        'point_of_sale._assets_pos': [
            # 'preparation_display' bootstrap customization layer
            'web/static/src/scss/functions.scss',
            # 'point_of_sale/static/src/scss/primary_variables.scss', TO DO - CREATE

            # 'webclient' bootstrap customization layer
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),

            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            # Import Bootstrap
            ('include', 'web._assets_bootstrap_backend'),

            # Icons
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/src/webclient/icons.scss',

            # scss variables and utilities
            'point_of_sale/static/src/scss/pos_variables_extra.scss',
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/fonts/fonts.scss',
            # JS boot
            'web/static/src/module_loader.js',
            # libs (should be loaded before framework)
            'point_of_sale/static/lib/**/*',
            'web/static/lib/luxon/luxon.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web_editor/static/lib/html2canvas.js',
            'web/static/lib/zxing-library/zxing-library.js',
            # JS framework
            ('include', 'web._assets_core'),
            ('remove', 'web/static/src/core/errors/error_handlers.js'), # error handling in PoS is different from the webclient
            # formatMonetary
            'web/static/src/views/fields/formatters.js',
            # barcode scanner
            'barcodes/static/src/barcode_service.js',
            'barcodes/static/src/js/barcode_parser.js',
            'barcodes_gs1_nomenclature/static/src/js/barcode_parser.js',
            'barcodes_gs1_nomenclature/static/src/js/barcode_service.js',
            'web/static/src/views/fields/parsers.js',
            'web/static/src/webclient/barcode/barcode_scanner.*',
            'web/static/src/webclient/barcode/ZXingBarcodeDetector.js',
            'web/static/src/webclient/barcode/crop_overlay.*',
            # bus service
            'bus/static/src/services/bus_service.js',
            'bus/static/src/bus_parameters_service.js',
            'bus/static/src/multi_tab_service.js',
            'bus/static/src/workers/*',
            # report download utils
            'web/static/src/webclient/actions/reports/utils.js',
            # PoS files
            'point_of_sale/static/src/**/*',
            ('remove', 'point_of_sale/static/src/backend/**/*'),
            # main.js boots the pos app, it is only included in the prod bundle as tests mount the app themselves
            ('remove', 'point_of_sale/static/src/app/main.js'),
            # tour system FIXME: can this be added only in test mode? Are there any onboarding tours in PoS?
            'web/static/lib/jquery/jquery.js',
            'web/static/src/legacy/js/libs/jquery.js',
            'web_tour/static/src/tour_pointer/**/*',
            'web_tour/static/src/tour_service/**/*',
        ],
        # Bundle that starts the pos, loaded on /pos/ui
        'point_of_sale.assets_prod': [
            ('include', 'point_of_sale._assets_pos'),
            'point_of_sale/static/src/app/main.js',
        ],
        # Bundle for the unit tests at /pos/ui/tests
        'point_of_sale.assets_qunit_tests': [
            ('include', 'point_of_sale._assets_pos'),
            # dependencies of web.tests_assets (in the web tests, these come from assets_backend)
            'web/static/tests/patch_translations.js',
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
            'web/static/tests/legacy/helpers/**/*',
            ('remove', 'web/static/tests/legacy/helpers/test_utils_tests.js'),

            'web/static/lib/fullcalendar/core/main.css',
            'web/static/lib/fullcalendar/daygrid/main.css',
            'web/static/lib/fullcalendar/timegrid/main.css',
            'web/static/lib/fullcalendar/list/main.css',
            'web/static/lib/fullcalendar/core/main.js',
            'web/static/lib/fullcalendar/interaction/main.js',
            'web/static/lib/fullcalendar/daygrid/main.js',
            'web/static/lib/fullcalendar/timegrid/main.js',
            'web/static/lib/fullcalendar/list/main.js',
            'web/static/lib/fullcalendar/luxon/main.js',

            'web/static/lib/zxing-library/zxing-library.js',

            'web/static/lib/ace/ace.js',
            'web/static/lib/ace/javascript_highlight_rules.js',
            'web/static/lib/ace/mode-python.js',
            'web/static/lib/ace/mode-xml.js',
            'web/static/lib/ace/mode-js.js',
            'web/static/lib/ace/mode-qweb.js',
            'web/static/lib/stacktracejs/stacktrace.js',
            ('include', "web.chartjs_lib"),

            # 'web/static/tests/legacy/main_tests.js',
            'web/static/tests/helpers/**/*.js',
            'web/static/tests/views/helpers.js',
            'web/static/tests/search/helpers.js',
            'web/static/tests/views/calendar/helpers.js',
            'web/static/tests/webclient/**/helpers.js',
            'web/static/tests/qunit.js',
            'web/static/tests/main.js',
            'web/static/tests/setup.js',

            ## END copy of web.tests_assets
            # pos unit tests
            'point_of_sale/static/tests/unit/**/*',
        ],
    },
    'license': 'LGPL-3',
}
