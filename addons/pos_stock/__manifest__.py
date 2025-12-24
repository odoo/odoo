{
    'name': 'PoS - Stock',
    'summary': 'Stock integration for PoS',
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale', 'stock_account'],
    'uninstall_hook': 'uninstall_hook',
    'auto_install': True,
    'data': [
        'security/pos_stock_security.xml',
        'security/ir.model.access.csv',
        'data/pos_stock_data.xml',
        'views/pos_order_view.xml',
        'views/product_view.xml',
        'views/pos_config_view.xml',
        'views/pos_session_view.xml',
        'views/res_config_settings_views.xml',
        'views/stock_reference_views.xml',
        'receipt/pos_order_receipt.xml',
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
        'web.assets_unit_tests_setup': [
            # we don't need css as we aren't testing the UI with hoot
            ('remove', 'pos_stock/static/src/app/components/popups/select_lot_popup/select_lot_popup.scss'),
        ],
        'web.assets_unit_tests': [
            'pos_stock/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
