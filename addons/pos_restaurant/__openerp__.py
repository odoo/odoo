# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Restaurant',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Restaurant extensions for the Point of Sale ',
    'description': """

=======================

This module adds several restaurant features to the Point of Sale:
- Bill Printing: Allows you to print a receipt before the order is paid
- Bill Splitting: Allows you to split an order into different orders
- Kitchen Order Printing: allows you to print orders updates to kitchen or bar printers

""",
    'depends': ['point_of_sale'],
    'website': 'https://www.odoo.com/page/point-of-sale',
    'data': [
        'restaurant_view.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
    ],
    'qweb':[
        'static/src/xml/multiprint.xml',
        'static/src/xml/splitbill.xml',
        'static/src/xml/printbill.xml',
        'static/src/xml/notes.xml',
        'static/src/xml/floors.xml',
    ],
    'demo': [
        'restaurant_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
