# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sell Courses",
    'summary': 'Sell your courses online',
    'description': """Sell your courses using the e-commerce features of the website.""",
    'category': 'Website/eLearning',
    'version': '1.0',

    'depends': ['website_slides', 'website_sale'],
    'installable': True,
    'data': [
        'data/product_data.xml',
        'report/sale_report_views.xml',
        'views/website_slides_menu_views.xml',
        'views/product_template_views.xml',
        'views/slide_channel_views.xml',
        'views/website_sale_templates.xml',
        'views/website_slides_templates.xml',
    ],
    'demo': [
        'data/product_demo.xml',
        'data/slide_demo.xml',
        'data/sale_order_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_slides/static/src/js/**/*',
            'website_sale_slides/static/src/xml/**/*',
        ],
        'web.assets_tests': [
            'website_sale_slides/static/tests/tours/*.js',
        ],
        'website.website_builder_assets': [
            'website_sale_slides/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
