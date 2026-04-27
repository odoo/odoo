{
    'name': 'eCommerce Rental with Stock Management',
    'category': 'Hidden',
    'summary': 'Sell rental products on your eCommerce and manage stock',
    'version': '1.0',
    'description': """
This module allows you to sell rental products in your eCommerce with
appropriate views and selling choices.
    """,
    'depends': ['website_sale_renting', 'website_sale_stock', 'sale_stock_renting'],
    'assets': {
        'web.assets_frontend': [
            'website_sale_stock_renting/static/src/xml/*.xml',
            ('after',
                'website_sale_renting/static/src/js/renting_mixin.js',
                'website_sale_stock_renting/static/src/js/renting_mixin.js'
            ),
            'website_sale_stock_renting/static/src/js/*.js',
        ],
        'web.assets_tests': [
            'website_sale_stock_renting/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
