# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Test Full eLearning Flow',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """
This module will test the main certification flow of Odoo.
It will install the e-learning, survey and e-commerce apps and make a complete
certification flow including purchase, certification, failure and success.
""",
    'depends': [
        'website_sale_product_configurator',
        'website_sale_slides',
        'website_slides_forum',
        'website_slides_survey',
        'payment_demo'
    ],
    'data': [
        'data/res_groups_data.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_tests': [
            'test_website_slides_full/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
