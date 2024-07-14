# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "bpost Shipping",
    'description': """
Send your shippings through bpost and track them online
=======================================================

Companies located in Belgium can take advantage of shipping with the
local Post company.

See: https://www.bpost.be/portal/goHome
    """,
    'category': 'Inventory/Delivery',
    'sequence': 330,
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_bpost_data.xml',
        'views/delivery_bpost_views.xml',
        'views/res_config_settings_views.xml',
        'views/bpost_request_templates.xml',
    ],
    'license': 'OEEL-1',
}
