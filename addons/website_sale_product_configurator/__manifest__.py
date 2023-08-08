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
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_product_configurator/static/src/js/website_sale_options.js',
            'sale_product_configurator/static/src/js/badge_extra_price/*',
            'sale_product_configurator/static/src/js/product/*',
            'sale_product_configurator/static/src/js/product_configurator_dialog/*',
            'sale_product_configurator/static/src/js/product_list/*',
            'sale_product_configurator/static/src/js/product_template_attribute_line/*',
        ],
        'web.assets_tests': [
            'website_sale_product_configurator/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
