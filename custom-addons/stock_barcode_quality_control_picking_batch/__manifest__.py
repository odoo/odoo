# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Barcode/Quality/Batch Transfer bridge module",
    'category': 'Hidden',
    'version': '1.0',
    'depends': [
        'quality_control_picking_batch',
        'stock_barcode_quality_control',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'stock_barcode_quality_control_picking_batch/static/**/*',
        ],
    }
}
