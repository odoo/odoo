{
    'name': 'Stock Barcode - Barcode Lookup',
    'category': 'Inventory/Inventory',
    'description': """
        This module allows you to create products from barcode using Barcode Lookup API Key
        if the product doesn't exists, inside barcode application.
    """,
    'depends': ['product_barcodelookup', 'stock_barcode'],
    'data': [
        "views/product_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'stock_barcode_barcodelookup/static/src/**/*.js',
            'stock_barcode_barcodelookup/static/src/**/*.xml',
        ],
        'web.assets_tests': [
            'stock_barcode_barcodelookup/static/tests/tours/**/*',
        ],
    },
    'license': 'OEEL-1',
}
