# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'POS - Sales',
    'version': '1.1',
    'category': 'Hidden',
    'sequence': 6,
    'summary': 'Link module between Point of Sale and Sales',
    'description': """

This module adds a custom Sales Team for the Point of Sale. This enables you to view and manage your point of sale sales with more ease.
""",
    'depends': ['point_of_sale', 'sale_management'],
    'data': [
        'data/pos_sale_data.xml',
        'security/pos_sale_security.xml',
        'security/ir.model.access.csv',
        'views/point_of_sale_report.xml',
        'views/sale_order_views.xml',
        'views/pos_order_views.xml',
        'views/product_views.xml',
        'views/sales_team_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_template.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_sale/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_sale/static/tests/tours/**/*',
        ],
    },
    'post_init_hook': '_pos_sale_post_init',
    'license': 'LGPL-3',
}
