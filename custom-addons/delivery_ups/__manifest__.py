# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "UPS Shipping (Legacy)",
    'description': "This is the legacy integration with UPS that is no longer supported. \
        Please install the new \"UPS Shipping\" module and uninstall this one as soon as possible. This integration will stop working in 2024.",
    'category': 'Inventory/Delivery',
    'sequence': 275,
    'version': '1.0',
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_ups_data.xml',
        'views/delivery_ups_view.xml',
        'views/res_config_settings_views.xml',
        'views/sale_views.xml',
        'views/res_partner_views.xml',
    ],
    'license': 'OEEL-1',
}
