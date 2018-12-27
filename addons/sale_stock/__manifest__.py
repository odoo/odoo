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

""",
    'depends': ['sale', 'stock_account'],
    'data': [
        'security/sale_stock_security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/stock_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_invoice_views.xml',
        'views/sale_stock_portal_template.xml',
        'views/stock_production_lot_views.xml',
        'report/sale_order_report_templates.xml',
        'report/stock_report_deliveryslip.xml',
        'data/sale_stock_data.xml',
        'wizard/stock_rules_report_views.xml',
    ],
    'demo': ['data/sale_order_demo.xml'],
    'installable': True,
    'auto_install': True,
}
