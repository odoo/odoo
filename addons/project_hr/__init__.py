from . import models


def post_init_hook(env):
    """Populate employee_ids / employee_id from existing user assignments.

    Without this hook, installing the module on a live database would
    immediately zero out all task assignments: employee_ids starts empty,
    _compute_user_ids fires, and user_ids becomes [].
    """
    # project.task — migrate user_ids → employee_ids
    tasks = (
        env["project.task"]
        .with_context(active_test=False)
        .search([("user_ids", "!=", False)])
    )
    for task in tasks:
        employees = env["hr.employee"].search(
            [("user_id", "in", task.user_ids.ids)]
        )
        if employees:
            task.employee_ids = employees

    # project.project — migrate user_id → employee_id
    projects = (
        env["project.project"]
        .with_context(active_test=False)
        .search([("user_id", "!=", False)])
    )
    for project in projects:
        employee = env["hr.employee"].search(
            [
                ("user_id", "=", project.user_id.id),
                ("company_id", "=", project.company_id.id),
            ],
            limit=1,
        )
        if employee:
            project.employee_id = employee
