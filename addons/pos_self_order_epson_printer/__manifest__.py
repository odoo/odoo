# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'POS Self Order Epson Printer',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Epson ePOS Printers in PoS Kiosk',
    'description': "Use Epson ePOS Printers without the IoT System in the PoS Kiosk",
    'depends': ['pos_epson_printer', 'pos_self_order'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'pos_self_order.assets': [
            'pos_epson_printer/static/src/app/epson_printer.js',
            'pos_epson_printer/static/src/app/components/epos_templates.xml',
            'pos_self_order_epson_printer/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
