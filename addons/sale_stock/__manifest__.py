# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales and Warehouse Management',
    'category': 'Sales/Sales',
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
        'views/sale_order_line_views.xml',
        'views/stock_route_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_stock_portal_template.xml',
        'views/stock_lot_views.xml',
        'views/res_users_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_reference_views.xml',

        'report/stock_report_deliveryslip.xml',
        'report/return_reason_report.xml',
        'report/return_slip_report.xml',

        'data/mail_templates.xml',
        'data/return_reason_data.xml',
        'data/sale_stock_data.xml',

        'wizard/stock_rules_report_views.xml',
    ],
    'demo': ['data/sale_order_demo.xml'],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'sale_stock/static/src/**/*',
            ('remove', 'sale_stock/static/src/iteractions/*'),
            ('remove', 'sale_stock/static/src/return_order_dialog/*'),
        ],
        'web.assets_frontend': [
            'sale/static/src/js/quantity_buttons/*',
            'sale_stock/static/src/iteractions/*',
            'sale_stock/static/src/return_order_dialog/*',
        ],
        'web.assets_tests': [
            'sale_stock/static/tests/tours/*.js',
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
