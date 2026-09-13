{
    "name": "Automation Rules",
    "version": "1.11",
    "category": "Sales/Sales",
    "description": """
This module allows to implement automation rules for any object.
================================================================

Use automation rules to automatically trigger actions for various screens.

**Example:** A lead created by a specific user may be automatically set to a specific
Sales Team, or an opportunity which still has status pending after 14 days might
trigger an automatic reminder email.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "bus",
        "digest",
        "mail",
        "resource",
        "sms",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/automation_runtime_rules.xml",
        "security/automation_canvas_rules.xml",
        "data/ir_cron_data.xml",
        "data/digest_data.xml",
        "data/ir_sequence_data.xml",
        "views/automation_rule_views.xml",
        "views/automation_runtime_views.xml",
        "views/automation_runtime_line_views.xml",
        "views/ir_actions_server_views.xml",
        "views/workflow_dag_views.xml",
        "views/automation_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "automation/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "automation/static/tests/**/*",
        ],
    },
}
