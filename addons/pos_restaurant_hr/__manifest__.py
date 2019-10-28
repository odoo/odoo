# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "pos_restaurant_hr",
    'category': "Hidden",
    'summary': 'Link module between PoS Restaurant and PoS HR',

    'description': """
    """,

    'depends': ['pos_restaurant', 'pos_hr'],

    'data': [
        'views/point_of_sale.xml',
    ],
    'installable': True,
    'auto_install': True,
    'qweb': ['static/src/xml/pos.xml'],
}
