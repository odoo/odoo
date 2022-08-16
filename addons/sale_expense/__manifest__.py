# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Expense',
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': 'Quotation, Sales Orders, Delivery & Invoicing Control',
    'description': """
Reinvoice Employee Expense
==========================

Create some products for which you can re-invoice the costs.
This module allow to reinvoice employee expense, by setting the SO directly on the expense.
""",
    'depends': ['sale_management', 'hr_expense'],
    'data': [
        'views/product_view.xml',
        'views/hr_expense_views.xml',
        'views/sale_order_views.xml',
        'views/hr_expense_sheet_views.xml',
    ],
    'demo': ['data/sale_expense_demo.xml'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'sale_expense/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'sale_expense/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
