{
    "name": "Sales Expense",
    "version": "1.0",
    "category": "Sales/Sales",
    "summary": "Quotation, Sales Orders, Delivery & Invoicing Control",
    "description": """
Reinvoice Employee Expense
==========================

Create some products for which you can re-invoice the costs.
This module allow to reinvoice employee expense, by setting the SO directly on the expense.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "sale",
        "hr_expense",
    ],
    "data": [
        "data/sale_expense_data.xml",
        "views/product_view.xml",
        "views/hr_expense_views.xml",
        "views/sale_order_views.xml",
    ],
    "auto_install": True,
}
