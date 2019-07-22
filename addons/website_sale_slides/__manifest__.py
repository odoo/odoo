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
        'report/sale_report_views.xml',
        'views/assets.xml',
        'views/website_slides_menu_views.xml',
        'views/slide_channel_views.xml',
        'views/website_slides_templates.xml',
    ],
    'demo': [
        'data/website_sale_slides_demo.xml',
    ],
}
