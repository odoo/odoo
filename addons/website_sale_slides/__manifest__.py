# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sell Courses",
    'summary': 'Sell your courses online',
    'description': """Sell your courses using the e-commerce features of the website.""",
    'category': 'Hidden',
    'version': '0.1',

    'depends': ['website_slides', 'website_sale'],
    'installable': True,
    'auto_install': True,
    'data': [
        'data/website_sale_slides_demo.xml',
        'views/slide_channel_views.xml',
    ]
}
