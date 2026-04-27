# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "DHL Express Shipping (Legacy)",
    'description': "This is the legacy integration with DHL Express that is no longer supported. \
        Please install the new \"DHL Express Shipping\" module and uninstall this one as soon as possible.",
    'category': 'Inventory/Delivery',
    'sequence': 285,
    'version': '1.0',
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_dhl_data.xml',
        'views/delivery_dhl_view.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'OEEL-1',
}
