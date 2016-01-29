# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'eCommerce Delivery',
    'category': 'Website',
    'summary': 'Add Delivery Costs to Online Sales',
    'website': 'https://www.odoo.com/page/e-commerce',
    'description': """
Delivery Costs
==============
""",
    'depends': ['website_sale', 'delivery'],
    'data': [
        'data/delivery_carrier_data.xml',
        'views/delivery_carrier_templates.xml',
        'views/delivery_carrier_views.xml'
    ],
    'demo': [
        'data/delivery_carrier_demo.xml'
    ],
}
