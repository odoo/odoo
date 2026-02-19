# -*- coding: utf-8 -*-
{
    'name': 'Invoice and Delivery address',
    'version': '16.0.1.0',
    'summary': 'Invoice and Delivery address',
    'sequence': 10,
    'description': '''
            Invoice and Delivery address
        ''',
    'category': 'Sales',
    'depends': ['base', 'web', 'sale_management'],
    'data': [
        'views/sale_order.xml'
    ],
    'installable': True,
    'application': False,
    "price": 0,
    "author": "Silver Touch Technologies Limited",
    "website": "https://www.silvertouch.com/",
    'images': ['static/description/banner.png'],
    "currency": "USD",
    'license': 'LGPL-3',
}
