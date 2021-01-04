# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Website Sale Blog",
    'summary': 'Link e-commerce products to website blog',
    'description': """
        Display related products of a blogpost on your website.
    """,
    'author': "Odoo SA",
    'category': 'Website/Website',
    'version': '0.1',
    'depends': ['website_sale', 'website_blog'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'auto_install': True,
}
