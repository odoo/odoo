{
    "name": "Contacts",
    "category": "Sales/CRM",
    "sequence": 150,
    "summary": "Centralize your address book",
    "description": """
        This module gives you a quick view of your contacts directory, accessible from your home page.
        You can track your vendors, customers and other contacts.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/ir.access.csv",
        "views/res_partner_age_range_views.xml",
        "views/res_partner_views.xml",
        "views/ir_ui_menu_views.xml",
    ],
    "demo": [
        "demo/res_partner_age_range_demo.xml",
        "demo/mail_demo.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "partner/static/tests/tours/**/*",
        ],
    },
    "application": True,
}
