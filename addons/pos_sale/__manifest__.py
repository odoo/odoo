# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_sale',
    'version': '1.0',
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
        'views/sales_team_views.xml',
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
