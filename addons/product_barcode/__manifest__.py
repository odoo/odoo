{
    'name': 'Product - Barcode',
    'summary': 'Scan barcodes to add products to sales or purchase orders',
    'depends': ['product', 'barcodes'],
    'assets': {
        'web.assets_backend': [
            'product_barcode/static/src/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
