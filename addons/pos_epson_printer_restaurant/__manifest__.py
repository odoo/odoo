# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_epson_printer_restaurant',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Epson Printers as Order Printers',
    'description': """

Use Epson Printers as Order Printers in the Point of Sale without the IoT Box
""",
    'depends': ['pos_epson_printer', 'pos_restaurant'],
    'data': [
        'views/point_of_sale_assets.xml',
        'views/pos_restaurant_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
