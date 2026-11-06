{
    "name": "Harvard University Website",
    "version": "19.0.1.0.0",
    "category": "Website/Education",
    "summary": "Harvard University Public Portal, Programs Directory, Admissions & Events",
    "author": "Harvard University",
    "license": "LGPL-3",
    "depends": [
        "website",
        "school_management",
    ],
    "data": [
        "data/website_menu_data.xml",
        "views/website/website_templates.xml",
        "views/academic/courses_templates.xml",
        "views/admission/admission_templates.xml",
        "views/dashboard/events_templates.xml",
        "views/core/jobs_templates.xml",
        "views/core/about_templates.xml",
        "views/core/contact_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "school_website/static/src/scss/school_website.scss",
        ],
    },
    "installable": True,
    "application": True,
}
