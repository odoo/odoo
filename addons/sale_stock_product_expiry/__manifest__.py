{
    'name': "Sale Stock Product Expiry",
    'category': 'Sales/Sales',
    'description': 'Modifications to the forecast widget on SO lines to show fresh stock, i.e. ignoring stock to be removed due to expiration.',
    'depends': ['sale_stock', 'product_expiry'],
    'auto_install': True,
    'license': 'LGPL-3',
    'author': 'Odoo S.A.',
    'assets': {
        'web.assets_tests': [
            'sale_stock_product_expiry/static/tests/tours/*.js',
        ],
        'web.assets_backend': [
            'sale_stock_product_expiry/static/src/**/*',
        ],
    },
}
