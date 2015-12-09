# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Product Catalog',
    'category': 'Sales Management',
    'description': """
        Adds a menu entry for 'Website Product Categories' in Product Catalog configuration menu when Website Sale is installed.
    """,
    'depends': ['website_sale', 'product_catalog'],
    'data': [
    	'views/website_product_catalog_views.xml',
    ],
    'auto_install': True,
}
