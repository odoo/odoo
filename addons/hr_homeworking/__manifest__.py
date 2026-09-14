{
    "name": "Remote Work",
    "version": "2.1",
    "category": "Human Resources/Remote Work",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "views/res_users.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_homeworking/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "hr_homeworking/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
