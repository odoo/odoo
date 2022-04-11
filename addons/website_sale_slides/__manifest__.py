# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sell Courses",
    'summary': 'Sell your courses online',
    'description': """Sell your courses using the e-commerce features of the website.""",
    'category': 'Hidden',
    'version': '1.0',

    'depends': ['website_slides', 'website_sale'],
    'installable': True,
    'data': [
        'data/product_data.xml',
        'report/sale_report_views.xml',
        'views/website_slides_menu_views.xml',
        'views/slide_channel_views.xml',
        'views/website_sale_templates.xml',
        'views/website_slides_templates.xml',
        'views/snippets.xml',
    ],
    'demo': [
        'data/product_demo.xml',
        'data/slide_demo.xml',
        'data/sale_order_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_slides/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}
