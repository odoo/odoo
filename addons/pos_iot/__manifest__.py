# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Point of Sale IoTBox integration",
    'summary': """Point of Sale IoTBox integration""",
    'description': """""",
    'category': 'Point of Sale',
    'version': '1.0.1',
    'depends': ['iot', 'point_of_sale'],
    'data': [
        'views/pos_config_view.xml',
    ],
    'installable': True,
    'application': False,
}
