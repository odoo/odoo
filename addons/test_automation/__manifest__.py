{
    "name": "Test - Base Automation",
    "version": "1.1",
    "category": "Hidden",
    "sequence": 9877,
    "summary": "Base Automation Tests: Ensure Flow Robustness",
    "description": """This module contains tests related to base automation. Those are
present in a separate module as it contains models used only to perform
tests independently to functional aspects of other models.

This module includes:
- Test models for automation testing (leads, projects)
- Comprehensive test suites (109+ integration tests)
- Demo automations showcasing various trigger types and patterns
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "automation",
        "automation_webhook",
        "test_mail",
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_tests": [
            "test_automation/static/tests/**/*",
        ],
    },
    "post_init_hook": "_post_init_hook",
}
