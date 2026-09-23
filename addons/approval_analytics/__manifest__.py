{
    "name": "Approval Analytics",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Approvals",
    "sequence": 191,
    "summary": "Category and approver statistics over the approval engine",
    "description": """
Approval Analytics
==================

The two SQL reports the approval engine is measured by, and the
menu entries that open them, under the Approvals application's Reporting
menu, which is why it follows ``approval_app`` rather than the engine.

Models
------
* ``approval.metrics`` -- per category: approval rate, average and median
  time, SLA compliance, cancelled count
* ``approver.performance`` -- per approver: response time, approval rate,
  workload

Both are live queries over ``approval.request`` and ``approval.approver``,
assembled by ``mixin.sql.report`` and inlined by the ORM on every read: no
relation is stored, so nothing is refreshed and no cron exists. That dependency
is why they are not in ``approval``: a module adopting ``mixin.approval`` needs
the engine, not the reporting stack.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "approval_app",
        "mixin_report_sql",
    ],
    "data": [
        "security/ir.access.csv",
        "views/approval_dashboard_views.xml",
        "views/approval_metrics_views.xml",
        "views/approver_performance_views.xml",
        "views/approval_analytics_menuitem_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "approval_analytics/static/src/scss/approval_dashboard.scss",
        ],
        "web.assets_web_dark": [
            "approval_analytics/static/src/scss/approval_dashboard.dark.scss",
        ],
    },
    "auto_install": True,
}
