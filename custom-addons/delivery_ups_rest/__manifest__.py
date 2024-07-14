# -*- coding: utf-8 -*-
{
    'name': "UPS Shipping",
    'summary': "Send your shippings through UPS and track them online",
    'category': 'Inventory/Delivery',
    'version': '0.1',
    'application': True,
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/ups_package_data.xml',
        'views/delivery_ups.xml',
        'views/sale_views.xml',
        'views/res_partner.xml',
    ],
    'license': 'OEEL-1',
}
