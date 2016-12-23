# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Invoice from Picking',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Create sale invoice from a delivery order',
    'description': """
Create sale invoice from a delivery order
=========================================

This module gives the possibility to create and print an invoice related to a sale order from a delivery order.
It adds a button "Create Invoice" on a delivery order, which will create, validate and print the invoice.
""",
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['sale_stock'],
    'data': [
        'views/sale_picking_invoice.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
