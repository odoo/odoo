{
    "name": "Delivery - Stock",
    "version": "1.0",
    "category": "Shipping Connectors",
    "description": """
Allows you to add delivery methods in pickings.
===============================================

When creating invoices from picking, the system is able to add and compute the shipping line.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "sale_stock",
        "delivery",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_view.xml",
        "views/delivery_view.xml",
        "views/delivery_portal_template.xml",
        "views/report_shipping.xml",
        "views/report_deliveryslip.xml",
        "views/report_package_barcode.xml",
        "wizards/choose_delivery_carrier_views.xml",
        "wizards/stock_put_in_pack_views.xml",
        "views/stock_package_type_views.xml",
        "views/stock_picking_type_views.xml",
        "views/stock_rule_views.xml",
        "views/stock_move_line_views.xml",
        "reports/product_templates.xml",
        "views/stock_delivery_menus.xml",
    ],
    "demo": [
        "demo/delivery_demo.xml",
    ],
    "auto_install": True,
}
