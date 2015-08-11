# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Loyalty Program',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Loyalty Program for the Point of Sale ',
    'description': """

=======================

This module allows you to define a loyalty program in
the point of sale, where the customers earn loyalty points
and get rewards.

""",
    'depends': ['point_of_sale'],
    'data': [
        'views/views.xml',
        'security/ir.model.access.csv',
        'views/templates.xml'
    ],
    'qweb': ['static/src/xml/loyalty.xml'],
    'demo': [
        'loyalty_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
