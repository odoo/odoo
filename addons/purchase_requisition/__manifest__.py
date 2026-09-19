{
    "name": "Purchase Agreements",
    "version": "0.3",
    "category": "Supply Chain/Purchase",
    "description": """
This module allows you to manage your Purchase Agreements.
===========================================================

Manage calls for tenders and blanket orders. Calls for tenders are used to get
competing offers from different vendors and select the best ones. Blanket orders
are agreements you have with vendors to benefit from a predetermined pricing.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "purchase",
    ],
    "data": [
        "security/purchase_requisition_security.xml",
        "security/ir.model.access.csv",
        "data/purchase_requisition_data.xml",
        "views/product_views.xml",
        "views/purchase_views.xml",
        "views/purchase_requisition_views.xml",
        "views/res_config_settings_views.xml",
        "reports/purchase_requisition_report.xml",
        "reports/report_purchaserequisition.xml",
        "wizards/purchase_requisition_alternative_warning.xml",
        "wizards/purchase_requisition_create_alternative.xml",
        "views/purchase_requisition_menus.xml",
    ],
    "demo": [
        "demo/purchase_requisition_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_requisition/static/src/*/**.js",
            "purchase_requisition/static/src/views/*/**.js",
            "purchase_requisition/static/src/*/**.scss",
            "purchase_requisition/static/src/*/**.xml",
        ],
    },
}
