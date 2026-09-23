MOVED_TO_ANALYTICS = (
    "access_approval_dashboard",
    "access_approval_dashboard_manager",
    "access_approval_metrics",
    "access_approval_metrics_manager",
    "access_approver_performance",
    "access_approver_performance_manager",
    "action_approval_dashboard",
    "action_approval_dashboard_view_singleton",
    "action_approval_metrics",
    "action_approver_performance",
    "approval_metrics_rule",
    "approver_performance_rule",
    "menu_approval_dashboard",
    "menu_approval_metrics",
    "menu_approver_performance",
    "view_approval_dashboard_form",
    "view_approval_metrics_graph",
    "view_approval_metrics_list",
    "view_approval_metrics_pivot",
    "view_approver_performance_graph",
    "view_approver_performance_list",
    "view_approver_performance_pivot",
)


def migrate(cr, version):
    """Hand the engine's reporting half to `approval_analytics`, and take both
    new modules along with the upgrade.

    `auto_install` fires only when a dependency is being INSTALLED, and an
    upgrade installs nothing, so a database that had the dashboard, the two SQL
    reports and the automation-backed Reset When would silently lose them on the
    way to 19.0.2.0.0. Marking the rows `to install` hands them to the same load,
    where the fields they now own are registered before the end-of-load cleanup
    could drop the columns they left behind.

    Re-pointing the external ids first means `approval_analytics` updates the
    records that are already there rather than creating second copies. Without
    it the end-of-load vacuum leaves the old access rows behind and the
    database ends up with two identical multi-company rules per report view.
    """
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'approval_analytics'
         WHERE module = 'approval'
           AND name = ANY(%s)
        """,
        [list(MOVED_TO_ANALYTICS)],
    )
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'to install'
         WHERE name IN ('approval_automation', 'approval_analytics')
           AND state = 'uninstalled'
        """
    )
