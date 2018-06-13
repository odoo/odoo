# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 15,
    'summary': 'Quotations, Sales Orders, Invoicing',
    'description': """
Manage sales quotations and orders
==================================

This application allows you to manage your sales goals in an effective and efficient manner by keeping track of all sales orders and history.

It handles the full sales workflow:

* **Quotation** -> **Sales order** -> **Invoice**

Preferences (only with Warehouse Management installed)
------------------------------------------------------

If you also installed the Warehouse Management, you can deal with the following preferences:

* Shipping: Choice of delivery at once or partial delivery
* Invoicing: choose how invoices will be paid
* Incoterms: International Commercial terms

You can choose flexible invoicing methods:

* *On Demand*: Invoices are created manually from Sales Orders when needed
* *On Delivery Order*: Invoices are generated from picking (delivery)
* *Before Delivery*: A Draft invoice is created and must be paid before delivery

With this module you can personnalize the sale order and invoice report with
categories, subtotals or page-breaks.

The Dashboard for the Sales Manager will include
------------------------------------------------
* My Quotations
* Monthly Turnover (Graph)
    """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sales_team', 'account', 'procurement', 'report', 'web_tour'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/sale_data.xml',
        'data/sale_tour.xml',
        'report/sale_report.xml',
        'data/mail_template_data.xml',
        'report/sale_report_views.xml',
        'report/sale_report_templates.xml',
        'report/invoice_report_templates.xml',
        'security/sale_security.xml',
        'security/ir.model.access.csv',
        'wizard/sale_make_invoice_advance_views.xml',
        'views/account_config_settings_views.xml',
        'views/sale_views.xml',
        'views/sales_team_views.xml',
        'views/res_partner_views.xml',
        'views/sale_config_settings_views.xml',
        'views/sale_templates.xml',
        'views/sale_layout_category_view.xml',
    ],
    'demo': [
        'data/sale_demo.xml',
        'data/product_product_demo.xml',
    ],
    'css': ['static/src/css/sale.css'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
