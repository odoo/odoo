# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_epson_printer',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Epson ePOS Printers in PoS',
    'description': """

Use Epson ePOS Printers without the IoT Box in the Point of Sale
""",
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_epson_printer/static/src/js/**/*',
        ],
        'web.assets_qweb': [
            'pos_epson_printer/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
