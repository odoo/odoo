{
    'name': "Sale Stock Product Expiry",
    'category': 'Sales/Sales',
    'description': 'Modifications to the forecast widget on SO lines to show fresh stock, i.e. ignoring stock to be removed due to expiration.',
    'version': '0.1',
    'depends': ['sale_stock', 'product_expiry'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
    'author': 'Odoo S.A.',
    'assets': {
        'web.assets_backend': [
            'sale_stock_product_expiry/static/src/**/*',
        ],
    },
}
