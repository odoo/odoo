# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales and Warehouse Management',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Quotation, Sales Orders, Delivery & Invoicing Control',
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
        'views/sale_order_views.xml',
        'views/stock_views.xml',
        'views/sale_config_settings_views.xml',
        'views/stock_config_settings_views.xml',
        'views/account_invoice_views.xml',
        'report/sale_order_report_templates.xml',
        'report/stock_report_deliveryslip.xml',
        'data/sale_stock_data.xml',
    ],
    'demo': ['data/sale_order_demo.xml'],
    'installable': True,
    'auto_install': True,
}
