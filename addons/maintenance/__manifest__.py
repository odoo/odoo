{
    "name": "Maintenance",
    "version": "1.2",
    "category": "Supply Chain/Maintenance",
    "summary": "Track equipment and manage maintenance requests",
    "description": """
Track equipment and maintenance requests""",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/maintenance",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "team",
    ],
    "data": [
        "security/maintenance.xml",
        "security/ir.model.access.csv",
        "data/maintenance_data.xml",
        "data/mail_activity_type_data.xml",
        "data/mail_message_subtype_data.xml",
        "views/maintenance_views.xml",
        "views/maintenance_plan_views.xml",
        "views/mail_activity_views.xml",
        "wizards/res_config_settings_views.xml",
        "views/maintenance_menus.xml",
    ],
    "demo": [
        "demo/maintenance_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "maintenance/static/src/**/*",
        ],
        "web.assets_tests": [
            "maintenance/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "maintenance/static/tests/*.test.js",
        ],
    },
    "application": True,
}
