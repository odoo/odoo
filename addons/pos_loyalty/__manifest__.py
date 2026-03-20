# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Point of Sale - Coupons & Loyalty",
    'version': '2.0',
    'category': 'Sales/Point Of Sale',
    'sequence': 6,
    'summary': 'Use Coupons, Gift Cards and Loyalty programs in Point of Sale',
    'depends': ['loyalty', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/default_barcode_patterns.xml',
        'data/gift_card_data.xml',
        'views/loyalty_card_views.xml',
        'views/loyalty_mail_views.xml',
        'views/pos_loyalty_menu_views.xml',
        'views/res_config_settings_view.xml',
        'views/loyalty_program_views.xml',
        'views/res_partner_views.xml',
        'receipt/pos_order_receipt.xml',
    ],
    'demo': [
        'data/pos_loyalty_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'pos_loyalty/static/src/portal/*',
        ],
        'point_of_sale._assets_pos': [
            'pos_loyalty/static/src/**/*',
            ('remove', 'pos_loyalty/static/src/portal/*'),
            ('remove', 'pos_loyalty/static/src/overrides/customer_display_overrides/customer_display.xml'),
        ],
        'point_of_sale.customer_display_assets': [
            'pos_loyalty/static/src/overrides/customer_display_overrides/customer_display.xml',
        ],
        'point_of_sale.customer_display_assets_test': [
            'pos_loyalty/static/tests/tours/customer_display_tour.js',
        ],
        'web.assets_tests': [
            'pos_loyalty/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_loyalty/static/tests/unit/**/*'
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
