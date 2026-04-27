# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "United States Postal Service (USPS) Shipping (Legacy)",
    'description': "This is the legacy integration with USPS. Please install the new \"United States Postal Service (USPS) Shipping\" module and uninstall this one as soon as possible.",
    'category': 'Inventory/Delivery',
    'sequence': 305,
    'version': '1.0',
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_usps_data.xml',
        'views/delivery_usps_view.xml',
        'views/delivery_usps_template.xml',
    ],
    'license': 'OEEL-1',
}
