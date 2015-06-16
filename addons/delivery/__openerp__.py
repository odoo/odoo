# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Delivery Costs',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Allows you to add delivery methods in sale orders and picking.
==============================================================

You can define your own carrier and delivery grids for prices. When creating 
invoices from picking, OpenERP is able to add and compute the shipping line.
""",
    'author': 'OpenERP SA',
    'depends': ['sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'delivery_view.xml',
        'partner_view.xml',
        'delivery_data.xml',
        'views/report_shipping.xml',
    ],
    'demo': ['delivery_demo.xml'],
    'test': [
        '../account/test/account_minimal_test.xml',
        'test/delivery_cost.yml',
        'test/stock_move_values_with_invoice_before_delivery.yml',
    ],
    'installable': True,
    'auto_install': False,
}
