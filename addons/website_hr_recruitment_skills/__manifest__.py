{
    "name": "Website HR Recruitment Skills",
    "category": "Website/Recruitment",
    "summary": "Enhance job applications with skills integration",
    "depends": [
        "website_hr_recruitment",
        "hr_skills",
    ],
    "description": """
Integrates skills management into the website recruitment process, helping applicants showcase their skills and improving job matching.
    """,
    "data": [
        "views/website_hr_recruitment_templates.xml",
        "data/config_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "website_hr_recruitment_skills/static/src/xml/website_form_editor.xml",
        ],
        "website.assets_wysiwyg": [
            "website_hr_recruitment_skills/static/src/xml/website_form_editor.xml",
        ],
        "website.website_builder_assets": [
            "website_hr_recruitment_skills/static/src/builder/plugins/form/form_option_plugin.js",
        ],
        "web.assets_tests": [
            "website_hr_recruitment_skills/static/tests/tours/website_hr_recruitment_skills.js",
        ],
    },
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
