# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Subcontract with Barcode",
    'summary': "Allows the subcontracting process with the barcode views",
    'category': 'Hidden',
    'version': '1.0',
    'description': """
This bridge module is auto-installed when the modules stock_barcode and mrp_subcontracting are installed.
    """,
    'depends': ['stock_barcode', 'mrp_subcontracting'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'stock_barcode_mrp_subcontracting/static/src/**/*.js',
            'stock_barcode_mrp_subcontracting/static/src/**/*.xml',
        ],
        'web.assets_tests': [
            'stock_barcode_mrp_subcontracting/static/tests/tours/**/*.js',
        ],
    }
}
