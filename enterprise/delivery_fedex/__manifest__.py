# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Fedex Shipping (Legacy)",
    'description': "This is the legacy integration with FedEx that is no longer supported. \
        Please install the new \"Fedex Shipping\" module and uninstall this one as soon as possible. This integration will stop working in 2024.",
    'category': 'Inventory/Delivery',
    'sequence': 295,
    'version': '1.0',
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_fedex.xml',
        'views/delivery_fedex.xml',
    ],
    'license': 'OEEL-1',
}
