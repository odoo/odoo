# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Barcode",
    'category': 'Inventory/Inventory',
    'summary': 'Process Manufacturing Orders from the barcode application',
    'version': '1.0',
    'depends': ['stock_barcode', 'mrp'],
    'auto_install': True,
    'license': 'OEEL-1',
    'data': [
        'data/data.xml',
        'views/mrp_production.xml',
        'views/stock_move_line.xml',
        'views/stock_picking_type.xml',
        'views/stock_scrap.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_barcode_mrp/static/src/**/*',
        ],
        'web.assets_tests': [
            'stock_barcode_mrp/static/tests/tours/**/*',
        ],
    }
}
