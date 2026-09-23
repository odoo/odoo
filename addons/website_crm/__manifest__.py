{
    "name": "Contact Form",
    "version": "2.1",
    "category": "Website/Website",
    "sequence": 54,
    "summary": "Generate leads from a contact form",
    "description": """
Add capability to your website forms to generate leads or opportunities in the CRM app.
Forms has to be customized inside the *Website Builder* in order to generate leads.

This module includes contact phone and mobile numbers validation.""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website",
        "crm",
    ],
    "data": [
        "security/ir.access.csv",
        "data/crm_lead_merge_template.xml",
        "data/ir_actions_data.xml",
        "data/ir_model_data.xml",
        "views/crm_lead_views.xml",
        "views/website_visitor_views.xml",
        "views/website_templates_contactus.xml",
    ],
    "assets": {
        "website.website_builder_assets": [
            "website_crm/static/src/js/website_crm_editor.js",
        ],
        "web.assets_tests": [
            "website_crm/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
