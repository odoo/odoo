{
    "name": "Automation Rules",
    "version": "1.0",
    "category": "Sales/Sales",
    "description": """
This module allows to implement automation rules for any object.
================================================================

Use automation rules to automatically trigger actions for various screens.

**Example:** A lead created by a specific user may be automatically set to a specific
Sales Team, or an opportunity which still has status pending after 14 days might
trigger an automatic reminder email.
    """,
    "depends": ["base", "digest", "resource", "mail", "sms"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "data/digest_data.xml",
        "data/ir_sequence_data.xml",
        "views/base_automation_views.xml",
        "views/automation_runtime_views.xml",
        "views/automation_runtime_line_views.xml",
        "views/ir_actions_server_views.xml",
        "views/workflow_dag_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "base_automation/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "base_automation/static/tests/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
