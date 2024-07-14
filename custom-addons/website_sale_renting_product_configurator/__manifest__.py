{
    'name': 'eCommerce Rental with Product Configurator',
    'category': 'Hidden',
    'summary': 'Sell rental products on your eCommerce and manage Product Configurator',
    'version': '1.0',
    'description': """
This module allows you to sell rental products with optional products in your eCommerce with
appropriate views and selling choices.
    """,
    'depends': ['website_sale_renting', 'website_sale_product_configurator'],
    'data': [
        'views/templates.xml',
    ],
    'demo':[
        'data/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_renting_product_configurator/static/src/js/**.js',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
