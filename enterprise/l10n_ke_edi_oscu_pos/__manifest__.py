{
    'name': 'Kenya - Point of Sale',
    'version': '1.0',
    'countries': ['ke'],
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_ke_edi_oscu_stock',
        'point_of_sale',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/pos_order.xml',
        'views/product_views.xml',
    ],
    'demo': [
        'demo/demo_product.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_ke_edi_oscu_pos/static/src/app/**/*',
            'l10n_ke_edi_oscu_pos/static/src/components/**/*',
            'l10n_ke_edi_oscu_pos/static/src/overrides/components/**/*',
            'l10n_ke_edi_oscu_pos/static/src/overrides/models/*.js',
        ],
        'web.assets_backend': [
            'l10n_ke_edi_oscu_pos/static/src/overrides/views/*.js',
            'l10n_ke_edi_oscu_pos/static/src/overrides/views/*.xml',
        ],
    },
    'post_init_hook': 'set_update_stock_real_time',
    'installable': True,
    'license': 'OEEL-1',
}
