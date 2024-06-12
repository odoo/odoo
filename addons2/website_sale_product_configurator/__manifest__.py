# -*- coding: utf-8 -*-
{
    'name': "Website Sale Product Configurator",
    'summary': "Bridge module for website_sale / sale_product_configurator",
    'description': """
Bridge module to make the website e-commerce compatible with the product configurator
    """,
    'category': 'Hidden',
    'depends': ['website_sale', 'sale_product_configurator'],
    'auto_install': True,
    'data': [
        'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            ('before', 'website_sale/static/src/js/website_sale.js', 'website_sale_product_configurator/static/src/js/sale_product_configurator_modal.js'),
            'website_sale/static/src/scss/product_configurator.scss',
            'website_sale_product_configurator/static/src/scss/website_sale_options.scss',
            'website_sale_product_configurator/static/src/js/website_sale_options.js',
        ],
        'web.assets_tests': [
            'website_sale_product_configurator/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
