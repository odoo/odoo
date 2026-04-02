{
    "name": "Tuition Management",
    "version": "19.0.1.6",
    "summary": "Manage tuition courses, students, tutors and registrations",
    "category": "Education",
    "author": "Auto Generated",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "mail", "calendar"],
    "data": [
        "security/ir.model.access.csv",
        "views/tuition_views.xml",
    ],
    "installable": True,
    "application": True,
    "post_init_hook": "_create_default_enquiry_stages",
}
