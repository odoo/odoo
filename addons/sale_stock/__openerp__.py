# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales and Warehouse Management',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Quotation, Sale Orders, Delivery & Invoicing Control',
    'description': """
Manage sales quotations and orders
==================================

This module makes the link between the sales and warehouses management applications.

Preferences
-----------
* Shipping: Choice of delivery at once or partial delivery
* Invoicing: choose how invoices will be paid
* Incoterms: International Commercial terms

You can choose flexible invoicing methods:

* *On Demand*: Invoices are created manually from Sales Orders when needed
* *On Delivery Order*: Invoices are generated from picking (delivery)
* *Before Delivery*: A Draft invoice is created and must be paid before delivery
""",
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['sale', 'stock_account'],
    'data': [
        'security/sale_stock_security.xml',
        'security/ir.model.access.csv',
        'company_view.xml',
        'sale_stock_view.xml',
        'sale_stock_workflow.xml',
        'stock_view.xml',
        'res_config_view.xml',
        'report/sale_report_view.xml',
        'account_invoice_view.xml',
    ],
    'demo': ['sale_stock_demo.xml'],
    'test': [
        '../account/test/account_minimal_test.xml',
        'test/sale_stock_users.yml',
        'test/cancel_order_sale_stock.yml',
        'test/picking_order_policy.yml',
        'test/prepaid_order_policy.yml',
        'test/sale_order_onchange.yml',
        'test/sale_order_canceled_line.yml',
    ],
    'installable': True,
    'auto_install': True,
}
