{
    "name": "Base Approval",
    "version": "19.0.2.10.2",
    "category": "Human Resources/Approvals",
    "sequence": 190,
    "summary": "Create and validate approval requests with delegation and escalation",
    "description": """
Base Approval
=============

Approval requests with configurable categories, multi-level approvers,
delegation and escalation.

Models
------
* ``approval.request`` / ``approval.approver`` -- the request and its approvers
* ``approval.category`` / ``approval.category.step`` -- request types and the
  steps their requests route by
* ``approval.rule`` / ``mixin.approval.threshold`` -- conditions on amount,
  quantity, date range or priority: a step applies by them, or they decide
  the request outright
* ``mixin.approval`` -- puts the workflow on any model
* ``approval.document.requirement`` -- documents a category demands
* ``approval.template`` -- reusable request presets
* ``approval.delegate.wizard`` / ``approval.decision.wizard`` /
  ``approval.refusal.reason`` -- delegation, decisions, refusal reasons

Depends on ``mail`` and nothing else, so that a module adopting
``mixin.approval`` takes one manifest row rather than the automation and
reporting stacks. ``approval_automation`` holds what needs ``automation``
(a category's flow, a binding's Reset When) and ``approval_analytics`` what
needs ``mixin_report_sql`` (the two SQL views). Both auto-install.

The Approvals application -- its menu, the generic request categories and
their demo -- is ``approval_app``. This module is what a module adopting
``mixin.approval`` pulls in, so it ships no application tile; its configuration
is reachable from Settings > Technical > Approvals.

A request creates an activity for each approver. Delegation reassigns those
activities to a substitute for a dated window; escalation reminds by priority.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "data/res_users_data.xml",
        "data/mail_activity_type_data.xml",
        "data/mail_message_subtype_data.xml",
        "data/ir_cron_data.xml",
        "data/approval_refusal_reason_data.xml",
        "reports/approval_request_report.xml",
        "views/approval_category_views.xml",
        "views/approval_category_step_views.xml",
        "views/approval_request_views.xml",
        "views/approval_refusal_reason_views.xml",
        "views/approval_rule_views.xml",
        "views/approval_binding_views.xml",
        "views/approval_gate_views.xml",
        "views/approval_observation_views.xml",
        "views/approval_request_template.xml",
        "wizards/approval_decision_wizard_views.xml",
        "wizards/approval_delegate_wizard_views.xml",
        "views/approval_technical_menuitem_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "approval/static/src/common/**",
            "approval/static/src/web/**",
            "approval/static/src/views/**",
            "approval/static/src/scss/**",
            (
                "remove",
                "approval/static/src/scss/*.dark.scss",
            ),
        ],
        "web.assets_web_dark": [
            "approval/static/src/scss/approval.dark.scss",
        ],
        "mail.assets_public": [
            "approval/static/src/common/**",
        ],
        "web.assets_tests": [
            "approval/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "approval/static/tests/**/*",
            (
                "remove",
                "approval/static/tests/tours/**/*",
            ),
        ],
    },
}
