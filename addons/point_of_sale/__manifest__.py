# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale',
    'version': '1.0.1',
    'category': 'Sales/Point of Sale',
    'sequence': 40,
    'summary': 'User-friendly PoS interface for shops and restaurants',
    'depends': ['stock_account', 'barcodes', 'web_editor', 'digest', 'phone_validation'],
    'uninstall_hook': 'uninstall_hook',
    'data': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'data/default_barcode_patterns.xml',
        'data/digest_data.xml',
        'data/pos_note_data.xml',
        'data/mail_template_data.xml',
        'data/point_of_sale_tour.xml',
        'wizard/pos_details.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_close_session_wizard.xml',
        'wizard/pos_daily_sales_reports.xml',
        'views/pos_assets_index.xml',
        'views/point_of_sale_report.xml',
        'views/point_of_sale_view.xml',
        'views/pos_note_view.xml',
        'views/pos_order_view.xml',
        'views/pos_category_view.xml',
        'views/product_combo_views.xml',
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
        'views/customer_display_index.xml',
        'views/account_move_views.xml',
        'views/pos_session_sales_details.xml'
    ],
    'demo': [
        'data/demo_data.xml',
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
        # Files in /static/src/app will be loaded in the PoS UI
        # Files in /static/tests/tours will be loaded in the backend in test mode
        # Files in /static/tests/unit will be loaded in the unit tests

        # web assets
        'web.assets_backend': [
            'point_of_sale/static/src/scss/pos_dashboard.scss',
            'point_of_sale/static/src/backend/tours/point_of_sale.js',
            'point_of_sale/static/src/backend/pos_kanban_view/*',
            'point_of_sale/static/src/app/utils/hooks.js',
        ],
        'web.assets_tests': [
            'barcodes/static/tests/helpers.js',
            'point_of_sale/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            # for the related_models.test.js
            'point_of_sale/static/src/app/models/related_models.js',
            # for the data_service.test.js
            'point_of_sale/static/src/app/models/utils/indexed_db.js',
            'point_of_sale/static/src/app/models/data_service_options.js',
            'point_of_sale/static/src/utils.js',
            'point_of_sale/static/src/app/models/data_service.js',
            'point_of_sale/static/tests/unit/**/*',
        ],

        # PoS assets

        'point_of_sale.base_app': [
            ("include", "web._assets_helpers"),
            ("include", "web._assets_backend_helpers"),
            ("include", "web._assets_primary_variables"),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_functions.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
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

        # Main PoS assets, they are loaded in the PoS UI
        'point_of_sale._assets_pos': [
            'web/static/src/scss/functions.scss',

            # JS boot
            'web/static/src/module_loader.js',
            # libs (should be loaded before framework)
            'point_of_sale/static/lib/**/*',
            'web/static/lib/luxon/luxon.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/lib/zxing-library/zxing-library.js',


            ('include', 'point_of_sale.base_app'),

            'web/static/src/core/colorlist/colorlist.scss',
            'web/static/src/webclient/webclient_layout.scss',

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
            # report download utils
            'web/static/src/webclient/actions/reports/utils.js',
            # PoS files
            'point_of_sale/static/src/**/*',
            ('remove', 'point_of_sale/static/src/backend/**/*'),
            ('remove', 'point_of_sale/static/src/customer_display/**/*'),
            # main.js boots the pos app, it is only included in the prod bundle as tests mount the app themselves
            ('remove', 'point_of_sale/static/src/app/main.js'),
            ("include", "point_of_sale.base_tests"),
            # account
            'account/static/src/helpers/*.js',
            'account/static/src/services/account_move_service.js',

            'mail/static/src/core/common/sound_effects_service.js',
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
        'point_of_sale.customer_display_assets': [
            ('include', 'point_of_sale.base_app'),
            "point_of_sale/static/src/app/generic_components/odoo_logo/*",
            "point_of_sale/static/src/app/generic_components/order_widget/*",
            "point_of_sale/static/src/app/generic_components/orderline/*",
            "point_of_sale/static/src/app/generic_components/centered_icon/*",
            "point_of_sale/static/src/utils.js",
            "point_of_sale/static/src/customer_display/**/*",
        ],
        'point_of_sale.customer_display_assets_test': [
            ('include', 'point_of_sale.base_tests'),
            "point_of_sale/static/tests/tours/**/*",
            "barcodes/static/tests/helpers.js",
            "web/static/tests/legacy/helpers/utils.js",
            "web/static/tests/legacy/helpers/cleanup.js",
        ],
        'point_of_sale.assets_debug': [
            'web_tour/static/src/tour_pointer/**/*',
            'web_tour/static/src/tour_service/**/*',
            ('remove', 'web_tour/static/src/tour_pointer/**/*.scss'),
            'web/static/tests/legacy/helpers/utils.js',
            'web/static/tests/legacy/helpers/cleanup.js',
            'barcodes/static/tests/helpers.js',
            'point_of_sale/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
