{
    "name": "Partnership / Membership",
    "version": "1.1",
    "category": "Sales/CRM",
    "description": """
This module allows you to manage all operations for managing memberships and partnerships.
==========================================================================================

You can easily assign grade to members/partners, with a specific pricelist.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "crm",
        "sale",
    ],
    "data": [
        "security/ir.access.csv",
        "data/res_partner_grade_data.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/res_partner_grade_views.xml",
        "views/product_template_views.xml",
        "views/product_pricelist_views.xml",
        "views/partnership_menu.xml",
    ],
}
