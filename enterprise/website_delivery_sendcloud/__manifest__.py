# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sendcould Locations for Website Delivery',
    'category': 'Inventory/Delivery',
    'summary': 'Allows website customers to choose delivery pick-up points',
    'description': 'This module allows ecommerce users to choose to deliver to Pick-Up points for the Sendcloud connector.',
    'depends': ['delivery_sendcloud', 'website_sale'],
    'data': [
        'views/delivery_sendcloud_view.xml',
    ],

    'auto_install': True,
    'license': 'OEEL-1',
}
