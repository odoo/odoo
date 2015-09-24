# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'eCommerce Optional Products',
    'category': 'Website',
    'website': 'https://www.odoo.com/page/e-commerce',
    'description': """
Odoo E-Commerce
==================

        """,
    'depends': ['website_sale'],
    'data': [
        'views/product_template_views.xml',
        'views/product_templates.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
}
