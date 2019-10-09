# -*- coding: utf-8 -*-
{
    'name': "Website Sale Product Configurator",
    'summary': """
        Bridge module for website_sale / sale_product_configurator""",
    'description': """
        Bridge module to make the website e-commerce compatible with the product configurator
    """,
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['website_sale', 'sale_product_configurator'],
    'auto_install': True,
    'data': [
        'views/assets.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
}
