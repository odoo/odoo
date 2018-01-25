# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Optional Products',
    'category': 'Website',
    'summary': 'Suggest optional products when adding to cart',
    'version': '1.0',
    'website': 'https://www.odoo.com/page/e-commerce',
    'description': """
Suggest optional products when shoppers add products to their cart (e.g. for computers: warranty, OS software, extra components).
Optional products are defined in the product form.
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
