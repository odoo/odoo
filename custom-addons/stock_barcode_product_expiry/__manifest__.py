# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Barcode Expiry",
    'category': 'Inventory/Inventory',
    'version': '1.0',
    'depends': ['stock_barcode', 'product_expiry'],
    'auto_install': True,
    'license': 'OEEL-1',
    'data': [
        'views/stock_move_line_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_barcode_product_expiry/static/src/**/*',
        ],
        'web.assets_tests': [
            'stock_barcode_product_expiry/static/tests/tours/**/*',
        ],
    },
}
