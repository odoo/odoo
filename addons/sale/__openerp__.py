# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Management',
    'version': '1.0',
    'category': 'Sales Management',
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


The Dashboard for the Sales Manager will include
------------------------------------------------
* My Quotations
* Monthly Turnover (Graph)
    """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sales_team','account', 'procurement', 'report'],
    'data': [
        'wizard/sale_make_invoice_advance.xml',
        'security/sale_security.xml',
        'security/ir.model.access.csv',
        'sale_sequence.xml',
        'sale_report.xml',
        'sale_data.xml',
        'sale_view.xml',
        'sales_team_view.xml',
        'res_partner_view.xml',
        'report/sale_report_view.xml',
        'data/mail_template_data.xml',
        'res_config_view.xml',
        'views/report_saleorder.xml',
        'views/sale.xml',
        'sales_team_dashboard.xml',
        'sale_tip_data.xml',
    ],
    'demo': ['sale_demo.xml',
             'sale_product_demo.xml',
             ],
    'css': ['static/src/css/sale.css'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
