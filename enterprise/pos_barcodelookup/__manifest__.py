{
    'name': 'POS - Barcode Lookup',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'This module enables product creation by scanning barcodes with a camera, utilizing the Barcode Lookup API Key.',
    'depends': ['point_of_sale', 'product_barcodelookup'],
    'data': [
        'views/product_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            "product_barcodelookup/static/src/widgets/**/*",
            "pos_barcodelookup/static/src/**/*",
        ],
        'web.assets_tests': [
            'pos_barcodelookup/static/tests/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
