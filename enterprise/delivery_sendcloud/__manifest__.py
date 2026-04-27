# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sendcloud Shipping",
    'description': "Shipping Integration with Sendcloud platform",
    'category': 'Inventory/Delivery',
    'sequence': 316,
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/message_templates.xml',
        'views/delivery_carrier_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/sendcloud_shipping_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'delivery_sendcloud/static/src/**/*.js',
            'delivery_sendcloud/static/src/**/*.xml',
        ],
    },
    'license': 'OEEL-1',
}
