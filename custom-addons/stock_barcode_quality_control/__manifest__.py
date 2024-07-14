# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Barcode Quality bridge module",
    'summary': "Allows the usage of quality checks within the barcode views",
    'category': 'Hidden',
    'version': '1.0',
    'description': """
This bridge module is auto-installed when the modules stock_barcode and quality_control are installed.
    """,
    'depends': ['stock_barcode', 'quality_control'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'stock_barcode_quality_control/static/src/**/*.js',
            'stock_barcode_quality_control/static/src/**/*.xml',
        ],
    }
}
