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
        'views/stock_route_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_stock_portal_template.xml',
        'views/stock_lot_views.xml',
        'views/res_users_views.xml',

        'report/report_stock_forecasted.xml',
        'report/sale_order_report_templates.xml',
        'report/stock_report_deliveryslip.xml',

        'data/mail_templates.xml',
        'data/sale_stock_data.xml',

        'wizard/stock_rules_report_views.xml',
        'wizard/sale_order_cancel_views.xml',
    ],
    'demo': ['data/sale_order_demo.xml'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'sale_stock/static/src/**/*',
            ('remove', 'sale_stock/static/src/legacy/**/*'),
        ],
        "web.assets_backend_legacy_lazy": [
            'sale_stock/static/src/legacy/**/*',
        ]
    },
    'license': 'LGPL-3',
}
