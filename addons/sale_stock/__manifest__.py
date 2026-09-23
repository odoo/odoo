{
    "name": "Sales Stock",
    "version": "1.5",
    "category": "Sales/Sales",
    "summary": "Quotation, Sales Orders, Delivery & Invoicing Control",
    "description": """
Manage sales quotations and orders
==================================

This module makes the link between the sales and warehouses management applications.

Preferences
-----------
* Shipping: Choice of delivery at once or partial delivery
* Invoicing: choose how invoices will be paid
* Incoterms: International Commercial terms

""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "stock_account",
        "sale",
        "base_order_stock",
    ],
    "data": [
        "security/ir.access.csv",
        "reports/sale_delivery_line_match_views.xml",
        "data/mail_templates.xml",
        "data/sale_stock_data.xml",
        "reports/customer_delay_report.xml",
        "views/sale_order_views.xml",
        "views/sale_order_line_views.xml",
        "views/stock_route_views.xml",
        "views/sale_stock_portal_template.xml",
        "views/stock_lot_views.xml",
        "views/res_partner_views.xml",
        "views/res_users_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_reference_views.xml",
        "reports/sale_order_report_templates.xml",
        "reports/stock_report_deliveryslip.xml",
        "wizards/stock_rules_report_views.xml",
        "wizards/res_config_settings_views.xml",
    ],
    "demo": [
        "demo/sale_order_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_stock/static/src/**/*",
        ],
        "web.assets_tests": [
            "sale_stock/static/tests/tours/*.js",
        ],
    },
    "auto_install": [
        "sale",
        "stock_account",
    ],
}
