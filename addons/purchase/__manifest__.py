# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Management',
    'version': '1.2',
    'category': 'Purchases',
    'sequence': 60,
    'summary': 'Purchase Orders, Receipts, Vendor Bills',
    'description': """
Manage goods requirement by Purchase Orders easily
==================================================

Purchase management enables you to track your vendors' price quotations and convert them into purchase orders if necessary.
Odoo has several methods of monitoring invoices and tracking the receipt of ordered goods. You can handle partial deliveries in Odoo, so you can keep track of items that are still to be delivered in your orders, and you can issue reminders automatically.

Odoo's replenishment management rules enable the system to generate draft purchase orders automatically, or you can configure it to run a lean process driven entirely by current production needs.

Dashboard / Reports for Purchase Management will include:
---------------------------------------------------------
* Request for Quotations
* Purchase Orders Waiting Approval
* Monthly Purchases by Category
* Receipt Analysis
* Purchase Analysis
    """,
    'website': 'https://www.odoo.com/page/purchase',
    'depends': ['stock_account'],
    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'views/account_invoice_views.xml',
        'data/purchase_data.xml',
        'data/purchase_data.yml',
        'report/purchase_reports.xml',
        'views/purchase_views.xml',
        'views/procurement_views.xml',
        'views/stock_views.xml',
        'views/stock_config_settings_views.xml',
        'views/res_partner_views.xml',
        'report/purchase_report_views.xml',
        'data/mail_template_data.xml',
        'views/res_config_views.xml',
        'views/account_config_settings_views.xml',
        'report/purchase_order_templates.xml',
        'report/purchase_quotation_templates.xml',
    ],
    'test': [
        '../account/test/account_minimal_test.xml',
        'test/stock_valuation_account.xml',
        'test/ui/purchase_users.yml',
        'test/process/run_scheduler.yml',
        'test/fifo_price.yml',
        'test/fifo_returns.yml',
        'test/process/cancel_order.yml',
        'test/ui/duplicate_order.yml',
        'test/ui/delete_order.yml',
        'test/average_price.yml',
    ],
    'demo': [
        'data/purchase_order_demo.yml',
        'data/purchase_demo.xml',
        'data/purchase_stock_demo.yml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
