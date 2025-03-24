# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale Mobile',
    'category': 'Hidden',
    'summary': 'Odoo Mobile Point of Sale module',
    'version': '1.0',
    'description': """
This module provides the point of sale function of the Odoo Mobile App.
        """,
    'depends': [
        'pos_enterprise',
        'web_mobile',
    ],
    'assets': {
        'point_of_sale.base_app': [
            'web_mobile/static/src/**/*',
        ],
        'point_of_sale._assets_pos': [
            'pos_mobile/static/src/**/*'
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
