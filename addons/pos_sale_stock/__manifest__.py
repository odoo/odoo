{
    'name': 'POS - Sales Stock',
    'category': 'Sales/Point of Sale',
    'summary': 'Link module between PoS Stock and Sales',
    'depends': ['pos_stock', 'pos_sale'],
    'data': [
        'views/stock_template.xml',
    ],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_sale_stock/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_sale_stock/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_sale_stock/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
