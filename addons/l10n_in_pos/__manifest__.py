# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Point of Sale',
    'description': """GST Point of Sale""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_in',
        'point_of_sale'
    ],
    'data': [
        'views/pos_order_line_views.xml',
        'views/pos_payment_method_views.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'data/pos_bill_data.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_in/static/src/helpers/hsn_summary.js',
            'l10n_in_pos/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_in_pos/static/tests/tours/**/*',
        ],
        'point_of_sale.customer_display_assets': [
            'l10n_in_pos/static/src/app/components/popups/qr_code_popup/qr_code_popup.xml',
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
