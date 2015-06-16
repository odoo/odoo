# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Invoice Picking Directly',
    'version': '1.0',
    'category' : 'Warehouse Management',
    'description': """
Invoice Wizard for Delivery.
============================

When you send or deliver goods, this module automatically launch the invoicing
wizard if the delivery is to be invoiced.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['delivery', 'stock'],
    'data': [],
    'demo': [],
    'test': ['../account/test/account_minimal_test.xml', 'test/stock_invoice_directly.yml'],
    'installable': True,
    'auto_install': False,
}
