# -*- coding: utf-8 -*-

{
    'name': 'Pos Multi Barcode',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'author': 'Webveer',
    'summary': "Allows you to create multiple barcode for a single product." ,
    'description': "Allows you to create multiple barcode for a single product.",
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_multi_barcode/static/src/js/pos.js',
            'pos_multi_barcode/static/src/xml/**/*',
        ],
    },
    'images': [
        'static/description/scan.jpg',
    ],
    'installable': True,
    'website': '',
    'auto_install': False,
    'price': 20,
    'currency': 'EUR',
}
