{
    "name": "Sales and Warehouse Management",
    "version": "1.0",
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
    "depends": ["sale", "stock_account"],
    "data": [
        "security/sale_stock_security.xml",
        "security/ir.model.access.csv",
        "data/mail_templates.xml",
        "data/sale_stock_data.xml",
        "report/customer_delay_report.xml",
        "views/sale_order_views.xml",
        "views/sale_order_line_views.xml",
        "views/stock_route_views.xml",
        "views/sale_stock_portal_template.xml",
        "views/stock_lot_views.xml",
        "views/res_partner_views.xml",
        "views/res_users_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_reference_views.xml",
        "report/sale_order_report_templates.xml",
        "report/stock_report_deliveryslip.xml",
        "wizard/stock_rules_report_views.xml",
        "wizard/res_config_settings_views.xml",
    ],
    "demo": ["demo/sale_order_demo.xml"],
    "installable": True,
    "auto_install": True,
    "assets": {
        "web.assets_backend": [
            "sale_stock/static/src/**/*",
        ],
        "web.assets_tests": [
            "sale_stock/static/tests/tours/*.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
