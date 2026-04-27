# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Barcode Quality MRP module",
    'category': 'Inventory/Inventory',
    'version': '1.0',
    'depends': ['stock_barcode', 'quality_mrp'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'stock_barcode_quality_mrp/static/src/**/*',
        ],
        'web.assets_tests': [
            'stock_barcode_quality_mrp/static/tests/tours/**/*',
        ],
    },
}
