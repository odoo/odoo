# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale Rental Stock',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 15,
    'summary': "Link between PoS and Stock Rental.",
    'depends': ['pos_sale', 'sale_stock_renting'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_tests': [
            'pos_sale_stock_renting/static/tests/**/*',
        ],
    },
}
