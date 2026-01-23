{
    'name': 'POS Self Order Loyalty',
    'summary': 'Allows customer identification and loyalty program usage in POS Self Order Mobile/Kiosk.',
    'category': 'Sales/Point Of Sale',
    'depends': ['pos_self_order', 'pos_loyalty', 'barcodes', 'barcodes_gs1_nomenclature'],
    'auto_install': ['pos_self_order', 'pos_loyalty'],
    'data': [],
    'assets': {
        'pos_self_order.assets': [
            'point_of_sale/static/src/app/utils/make_awaitable_dialog.js',
            'pos_self_order_loyalty/static/src/**/*',
            'web/static/src/core/barcode/**/*',
            'pos_loyalty/static/src/app/models/**/*',
            ('remove', 'pos_loyalty/static/src/app/models/data_service_options.js'),
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
