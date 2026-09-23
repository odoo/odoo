{
    "name": "HR Gamification",
    "version": "1.1",
    "category": "Human Resources",
    "description": """Use the HR resources for the gamification process.

The HR officer can now manage challenges and badges.
This allow the user to send badges to employees instead of simple users.
Badge received are displayed on the user profile.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "gamification",
        "hr",
    ],
    "data": [
        "security/gamification_security.xml",
        "security/ir.model.access.csv",
        "wizards/gamification_badge_user_wizard_views.xml",
        "views/gamification_views.xml",
        "views/hr_employee_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_gamification/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "hr_gamification/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
