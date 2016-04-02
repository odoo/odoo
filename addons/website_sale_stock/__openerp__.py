# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Sale Stock - Website Delivery information',
    'description': """
    Display delivery orders (picking) infos on the website
""",
    'depends': [
        'website_sale',
        'sale_stock',
    ],
    'auto_install': True,
    'data': [
        'views/templates.xml',
    ]
}
