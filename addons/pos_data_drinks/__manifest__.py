# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale Common Data Drinks',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 99,
    'summary': 'Common Drinks data for points of sale',
    'description': """
        Common drinks data for points of sale
    """,
    'depends': ['point_of_sale'],
    'data': [
        'data/pos_data_drinks.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'website': 'https://www.odoo.com/page/point-of-sale',
    'auto_install': False,
}
