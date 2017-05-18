# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Expense',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Quotation, Sales Orders, Delivery & Invoicing Control',
    'description': """
Module used for demo data
=========================

Create some products for which you can re-invoice the costs.
This module does not add any feature, despite a few demo data to
test the features easily.
""",
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['sale_management', 'hr_expense'],
    'data': [
        'views/product_view.xml',
    ],
    'demo': ['sale_expense_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': True,
}
