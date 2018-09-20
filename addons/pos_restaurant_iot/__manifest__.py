# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Restaurant IoTBox integration",
    'summary': """Restaurant IoTBox integration""",
    'description': """""",
    'category': 'Point of Sale',
    'version': '1.0.1',
    'depends': ['pos_iot', 'pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_printer_views.xml',
        'views/pos_config_view.xml',
    ],
    'installable': True,
    'application': False,
}
