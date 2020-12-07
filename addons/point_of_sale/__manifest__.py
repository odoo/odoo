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
        'views/pos_session_view.xml',
        'views/point_of_sale_sequence.xml',
        'data/point_of_sale_data.xml',
        'views/pos_order_report_view.xml',
        'views/account_statement_view.xml',
        'views/res_config_settings_views.xml',
        'views/digest_views.xml',
        'views/res_partner_view.xml',
        'views/report_userlabel.xml',
        'views/report_saledetails.xml',
        'views/point_of_sale_dashboard.xml',
    ],
    'demo': [
        'data/point_of_sale_demo.xml',
    ],
    'installable': True,
    'application': True,
    'website': 'https://www.odoo.com/page/point-of-sale-shop',
    'assets': {
        'web.assets_tests': [
            'point_of_sale/static/tests/tours/**/*',
        ],
        'point_of_sale.assets': [
            'web/static/fonts/fonts.scss',
            'web/static/lib/fontawesome/css/font-awesome.css',
            'point_of_sale/static/src/css/pos.css',
            'point_of_sale/static/src/css/keyboard.css',
            'point_of_sale/static/src/css/pos_receipts.css',
            'web/static/src/scss/fontawesome_overridden.scss',
            'point_of_sale/static/lib/**/*.js',
            'point_of_sale/static/src/js/ui/**/*.js',
        ],
        'point_of_sale.main': [
            'point_of_sale/static/src/js/pos_main.js',
        ],
        'web.assets_backend': [
            'point_of_sale/static/src/scss/pos_dashboard.scss',
            'point_of_sale/static/src/js/backend/**/*.js',
        ],
        'point_of_sale.pos_assets_backend': [
            ('include', 'web.assets_backend'),
        ],
        'web.assets_qweb': [
            'point_of_sale/static/src/xml/**/*',
        ],
    }
}
