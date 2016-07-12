# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'eCommerce Optional Products',
    'category': 'Website',
    'version': '1.0',
    'website': 'https://www.odoo.com/page/e-commerce',
    'description': """
Odoo E-Commerce
==================

        """,
    'depends': ['website_sale'],
    'data': [
        'views/product_views.xml',
        'views/website_sale_options_templates.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
