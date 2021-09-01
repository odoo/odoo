# -*- coding: utf-8 -*-
# License: OPL-1
{
    'name': "POS Scan Camera",
    'version': '1.0',
    'category': 'Point of Sale',
    'author': 'TL Technology',
    'sequence': 0,
    'summary': 'Scan everything barcode viva Camera',
    'description': 'Scan everything barcode viva Camera\n'
                   'Only Supported SSL (https) Odoo server domain\n'
                   'Support Scan barcode clients, products ....',
    'depends': ['point_of_sale'],
    'data': [
        'template/template.xml',
        'views/PosConfig.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'price': '0',
    'website': 'http://posodoo.com',
    'application': True,
    'images': ['static/description/icon.png'],
    'support': 'thanhchatvn@gmail.com',
    "currency": 'EUR',
    "license": "OPL-1",
}
