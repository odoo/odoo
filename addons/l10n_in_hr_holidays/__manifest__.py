{
    "name": "India - Time Off",
    "version": "1.0",
    "category": "Human Resources/Time Off",
    "summary": "Leave Management of Indian Localization",
    "description": "The Indian Time Off module provides additional features to the application. With it, you'll be able to define Sandwich Leaves on your time off type, including weekends or holidays in the duration of the employee leave's request.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr_holidays",
    ],
    "countries": [
        "in",
    ],
    "data": [
        "security/ir.access.csv",
        "views/hr_leave_views.xml",
        "views/hr_leave_type_views.xml",
        "views/l10n_in_hr_leave_optional_holiday_views.xml",
        "views/l10n_in_hr_holidays_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_in_hr_holidays/static/src/**/*",
        ],
    },
    "auto_install": [
        "hr_holidays",
    ],
}
