{
    'name': "Product Barcode Lookup for eCommerce",
    'description': "This module allows you to display data get from barcode lookup API in the eCommerce",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['product_barcodelookup', 'website_sale'],
    'data': [
        'data/product_data.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'website_product_barcodelookup/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
