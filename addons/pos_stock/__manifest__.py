# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS - Stock',
    'summary': 'Handle stock logic for POS.',
    'depends': ['point_of_sale', 'stock_account'],
    'auto_install': True,
    'data': [
        'security/pos_stock_security.xml',
        'security/ir.model.access.csv',
        'views/pos_order_view.xml',
        'views/product_view.xml',
        'views/pos_config_view.xml',
        'views/pos_session_view.xml',
        'views/res_config_settings_views.xml',
        'views/stock_reference_views.xml',
        'receipt/pos_order_receipt.xml',
    ],
    'demo': [
        'data/pos_stock_data.xml',
    ],
    'assets': {
        # Main PoS assets, they are loaded in the PoS UI
        'point_of_sale._assets_pos': [
            'pos_stock/static/src/**/*',
            ('remove', 'pos_stock/static/src/customer_display/**/*'),
        ],
        'point_of_sale.customer_display_assets': [
            "pos_stock/static/src/app/components/orderline/*",
            "pos_stock/static/src/customer_display/**/*",
        ],
        'web.assets_tests': [
            'pos_stock/static/tests/pos/tours/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
