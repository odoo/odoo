# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Loyalty Program',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Loyalty Program',
    'description': """

This module allows you to define a loyalty program 
where customers earn loyalty points and get rewards.

""",
    'depends': [
        'product',
        'reward',
    ],
    'data': [
        'views/loyalty_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/loyalty_demo.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
