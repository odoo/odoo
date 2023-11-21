# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_sale_gift_card',
    'version': '1.1',
    'category': 'Hidden',
    'sequence': 6,
    'summary': 'Link module between pos_sale and gift_card',
    'description': """
""",
    'depends': ['pos_sale', 'gift_card'],
    'assets': {
        'point_of_sale.assets': [
            'pos_sale_gift_card/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_sale_gift_card/static/tests/**/*',
        ]
    },
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
