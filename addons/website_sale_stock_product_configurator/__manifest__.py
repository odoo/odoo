# -*- coding: utf-8 -*-
{
    'name': "Website Sale Stock Product Configurator",
    'summary': """
        Bridge module for website_sale_stock / sale_product_configurator""",
    'description': """
        Bridge module to make the website e-commerce stock management compatible with the product configurator
    """,
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['website_sale_stock', 'sale_product_configurator'],
    'auto_install': True,
    'data': [
        'views/product_configurator_templates.xml',
    ],
}
