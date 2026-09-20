{
    "name": "Resource",
    "version": "1.20",
    "category": "Hidden",
    "description": """
Module for resource management.
===============================

A resource represent something that can be scheduled (a developer on a task or a
work center on manufacturing orders). This module manages a resource calendar
associated to every resource. It also manages the leaves of every resource.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "data/resource_data.xml",
        "security/ir.model.access.csv",
        "security/resource_security.xml",
        "views/resource_reservation_views.xml",
        "views/resource_assignment_views.xml",
        "views/resource_resource_views.xml",
        "views/resource_role_views.xml",
        "views/resource_schedule_exception_views.xml",
        "views/resource_calendar_attendance_views.xml",
        "views/resource_calendar_views.xml",
        "views/menuitems.xml",
    ],
    "demo": [
        "demo/resource_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "resource/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "resource/static/tests/**/*",
        ],
    },
}
