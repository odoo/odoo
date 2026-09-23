{
    "name": "Customer References",
    "version": "1.0",
    "category": "Website/Website",
    "summary": "Publish your customer references",
    "description": """
Publish your customers as business references on your website to attract new potential prospects.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website_crm_partner_assign",
        "website_partner",
        "website_google_map",
    ],
    "data": [
        "views/website_customer_templates.xml",
        "views/res_partner_views.xml",
        "security/ir.access.csv",
        "views/website_customer_menus.xml",
    ],
    "demo": [
        "demo/res_partner_demo.xml",
    ],
    "assets": {
        "website.website_builder_assets": [
            "website_customer/static/src/website_builder/**/*",
        ],
    },
}
