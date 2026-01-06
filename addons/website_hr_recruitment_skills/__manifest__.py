{
    "name": "Website HR Recruitment Skills",
    "category": "Website/Recruitment",
    "summary": "Enhance job applications with skills integration",
    "depends": [
        "website_hr_recruitment",
        "hr_recruitment_skills",
    ],
    "description": """
Integrates skills management into the website recruitment process, helping applicants showcase their skills and improving job matching.
    """,
    "data": [
        "data/config_data.xml",
    ],
    "assets": {
        "website.assets_inside_builder_iframe": [
            "website_hr_recruitment_skills/static/src/xml/*.xml",
        ],
        "web.assets_tests": [
            "website_hr_recruitment_skills/static/tests/tours/**/*",
        ],
    },
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
