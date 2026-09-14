{
    "name": "Sales Teams",
    "version": "1.9",
    "category": "Sales/Sales",
    "summary": "Sales Teams",
    "description": """
Using this application you can manage Sales Teams with CRM and/or Sales
=======================================================================
 """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/crm",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/sales_team_security.xml",
        "security/ir.model.access.csv",
        "data/crm_team_data.xml",
        "views/crm_tag_views.xml",
        "views/crm_team_views.xml",
        "views/crm_team_member_views.xml",
        "views/mail_activity_views.xml",
    ],
    "demo": [
        "demo/crm_team_demo.xml",
        "demo/crm_tag_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sales_team/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "sales_team/static/tests/**/*",
        ],
    },
}
