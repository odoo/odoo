# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Test Certification Flow',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module will test the main certification flow of Odoo.
It will install the e-learning, survey and e-commerce apps and make a complete
certification flow including purchase, certification, failure and success.
""",
    'depends': ['website_sale', 'website_slides_survey', 'payment_test'],
    'data': [
        'data/certification_flow_data.xml',
        'views/templates.xml',
    ],
    'installable': True,
}
