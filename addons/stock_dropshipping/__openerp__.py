# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Drop Shipping',
    'version': '1.0',
    'category': 'Warehouse',
    'summary': 'Drop Shipping',
    'description': """
Manage drop shipping orders
===========================

This module adds a pre-configured Drop Shipping picking type
as well as a procurement route that allow configuring Drop
Shipping products and orders.

When drop shipping is used the goods are directly transferred
from vendors to customers (direct delivery) without
going through the retailer's warehouse. In this case no
internal transfer document is needed.

""",
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['purchase', 'sale_stock'],
    'data': ['stock_dropshipping.xml'],
    'test': [
        '../account/test/account_minimal_test.xml',
        '../stock_account/test/stock_valuation_account.xml',
        'test/cancellation_propagated.yml',
        'test/crossdock.yml',
        'test/dropship.yml',
        'test/procurementexception.yml',
        'test/lifo_price.yml'
    ],
    'installable': True,
    'auto_install': False,
}
