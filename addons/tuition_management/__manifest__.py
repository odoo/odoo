{
    "name": "Tuition Management",
    "version": "19.0.1.0.0",
    "summary": "Manage tuition courses, students, tutors and registrations",
    "category": "Education",
    "author": "Auto Generated",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "mail", "portal"],
    "data": [
        "security/ir.model.access.csv",
        "views/tuition_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
    "application": True,
    "post_init_hook": "create_default_time_slots",
}
