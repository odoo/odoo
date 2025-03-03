{
    'name': 'POS Customer Display',
    'version': '1.0',
    'summary': 'POS customer display',
    'depends': ['point_of_sale'],
    'application': True,
    'installable': True,
    'assets': {
        'point_of_sale.assets_prod': [
            'pos_customer_display/static/src/pos_order.js',
        ],
        'point_of_sale.customer_display_assets': [
            'pos_customer_display/static/src/customer_display/**/*',
        ],
    },
    'license': 'LGPL-3',
}
