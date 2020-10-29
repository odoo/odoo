# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Fix register payment wizard with 'payment' module",
    'category': 'Hidden',
    'version': '1.0',
    'description': """""",
    'depends': ['payment'],
    'data': [
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
