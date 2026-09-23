{
    "name": "Social Media",
    "version": "0.2",
    "category": "Marketing/Social Marketing",
    "summary": "Social media connectors for company settings.",
    "description": """
The purpose of this technical module is to provide a front for
social media configuration for any other module that might need it.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/ir.access.csv",
        "views/res_company_views.xml",
    ],
    "demo": [
        "demo/res_company_demo.xml",
    ],
}
