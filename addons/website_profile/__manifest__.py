{
    "name": "Website profile",
    "version": "1.0",
    "category": "Website/Website",
    "summary": "Access the website profile of the users",
    "description": "Allows to access the website profile of the users and see their statistics (karma, badges, etc..)",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website_partner",
        "gamification",
    ],
    "data": [
        "data/mail_template_data.xml",
        "views/gamification_badge_views.xml",
        "views/website_profile.xml",
        "views/website_views.xml",
        "security/ir.access.csv",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_profile/static/src/scss/website_profile.scss",
            "website_profile/static/src/components/**/*",
            "website_profile/static/src/interactions/**/*",
            (
                "remove",
                "website_profile/static/src/interactions/**/*.edit.js",
            ),
            (
                "include",
                "html_editor._assets_editor",
            ),
        ],
        "website.assets_inside_builder_iframe": [
            "website_profile/static/src/**/*.edit.js",
        ],
        "web.assets_tests": [
            "website_profile/static/tests/tours/tour_website_profile_description.js",
        ],
    },
}
