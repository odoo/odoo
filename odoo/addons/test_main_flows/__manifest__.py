{
    "name": "Test Main Flow",
    "version": "1.0",
    "category": "Hidden/Tests",
    "description": """
This module will test the main workflow of Odoo.
It will install some main apps and will try to execute the most important actions.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web_tour",
        "crm",
        "sale_timesheet",
        "purchase_stock",
        "mrp",
        "account",
    ],
    "data": [
        "security/ir.access.csv",
    ],
    "assets": {
        "web.assets_tests": [
            "test_main_flows/static/tests/tours/*.js",
        ],
    },
    "post_init_hook": "_auto_install_enterprise_dependencies",
}
