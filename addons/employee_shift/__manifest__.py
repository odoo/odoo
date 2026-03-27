{
    "name": "Employee Shift Management",
    "version": "19.0.1.0.0",
    "summary": "Create shifts, assign employees and view shifts in a calendar",
    "category": "Human Resources",
    "author": "Auto Generated",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "hr", "calendar"],
    "data": [
        "security/ir.model.access.csv",
        "views/employee_shift_views.xml",
    ],
    "post_init_hook": "employee_shift_post_init",
    "installable": True,
    "application": True,
}
