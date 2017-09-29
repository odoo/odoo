# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Expense',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Quotation, Sales Orders, Delivery & Invoicing Control',
    'description': """
Reinvoice Employee Expense
==========================

Create some products for which you can re-invoice the costs.
This module allow to reinvoice employee expense, by setting the SO directly on the expense.
""",
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['sale_management', 'hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'security/sale_expense_security.xml',
        'views/product_view.xml',
        'views/hr_expense_views.xml',
    ],
    'demo': ['sale_expense_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': True,
}
