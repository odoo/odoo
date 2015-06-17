# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Carrier Grid',
    'version': '1.0',
    'category': 'Technical Features',
    'description': """
Allows you to add delivery methods in sale orders and picking
=============================================================

You can define your own carrier and delivery grids for prices. When creating
invoices from picking, Odoo is able to add and compute the shipping line.


Interface with Shipping Providers
=================================
Send your packages through the main shipping providers, get the price,
the shipping slip and the tracking number of your packages.
""",
    'author': 'Odoo SA',
    'depends': ['delivery'],
    'data': [
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
}
