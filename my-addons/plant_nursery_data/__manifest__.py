# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Plant Nursery Data',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Data for Plant Nursery',
    'depends': ['plant_nursery'],
    'data': [
        'data/base_data.xml',
        'data/customer_data.xml',
        'data/plant_misc_data.xml',
        'data/plant_data.xml',
        'data/mail_thread_data.xml',
        'data/order_data.xml',
        'data/discuss_data.xml',
        'data/rating_data.xml',
        'data/mail_data.xml',  # to define manually
        'data/contact_private_data.xml',  # to define manually
        'data/sms_private_data.xml',  # to define manually
        'data/gateway_private_data.xml',  # to define manually
    ],
    'demo': [
        'data/base_demo.xml',
        'data/plant_demo.xml',
        'data/discuss_demo.xml',
        'data/rating_demo.xml',
        'data/contact_private_demo.xml',  # to define manually
    ],
    'css': [],
    'auto_install': False,
    'application': False,
}
