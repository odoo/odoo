{
    'name': "Product Barcode Lookup",
    'description': "This module allows you to create products from barcode using Barcode Lookup API Key",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['product'],
    'data': [
        'data/product_data.xml',
        'views/product_product_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_barcodelookup/static/src/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
