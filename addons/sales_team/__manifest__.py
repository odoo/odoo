{
    "name": "Sales Teams",
    "version": "2.0",
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
        "team",
    ],
    "data": [
        "security/sales_team_security.xml",
        "security/ir.model.access.csv",
        "data/team_team_data.xml",
        "views/crm_tag_views.xml",
        "views/team_team_views.xml",
        "views/mail_activity_views.xml",
    ],
    "demo": [
        "demo/team_team_demo.xml",
        "demo/crm_tag_demo.xml",
    ],
}
