# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales',
    'version': '1.0',
    'category': 'Sales/Sales',
    'sequence': 5,
    'summary': 'From quotations to invoices',
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


With this module you can personnalize the sales order and invoice report with
categories, subtotals or page-breaks.

The Dashboard for the Sales Manager will include
------------------------------------------------
* My Quotations
* Monthly Turnover (Graph)
    """,
    'website': 'https://www.odoo.com/app/sales',
    'depends': ['sale', 'digest'],
    'data': [
        'security/sale_management_security.xml',
        'data/digest_data.xml',
        'views/sale_portal_templates.xml',
        'views/sale_order_template_views.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'data/digest_data.xml',
        'views/sale_management_views.xml',
        'views/digest_views.xml',
        'views/sale_order_views.xml',
        'report/sale_report_templates.xml',
    ],
    'demo': [
        'data/sale_order_template_demo.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_frontend': [
            'sale_management/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}
