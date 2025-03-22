# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_sale_loyalty',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 6,
    'summary': 'Link module between pos_sale and pos_loyalty',
    'description': """
This module correct some behaviors when both module are installed.
""",
    'depends': ['pos_sale', 'pos_loyalty'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_sale_loyalty/static/src/js/**/*.js',
        ],
        'web.assets_tests': [
            'pos_sale_loyalty/static/src/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
