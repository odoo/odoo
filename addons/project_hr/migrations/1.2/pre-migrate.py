import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Keep every project manager the database already has.

    `project.project.user_id` is composed here from `employee_id.user_id`, and
    gains `direct_user_id` in this version for a manager who holds no employee
    record. Adding that dependency makes the ORM recompute the field for every
    row, and the recompute answers an empty `employee_id` with an empty manager.

    A project can carry a manager and no employee, because `user_id` was a plain
    field before this module composed it and the compute has never been triggered
    on those rows. Measured on the production database: of 42 projects, 41 name a
    manager, 39 of those have no `employee_id` and would lose the manager on
    upgrade. All 39 managers do hold an employee record, so they are matched to
    it; none of them needs `direct_user_id` today. The field exists because a
    manager is allowed to be a user with no employee, not because production has
    one -- and the first statement below is what keeps such a manager when it does.
    """
    cr.execute("""
        ALTER TABLE project_project
        ADD COLUMN IF NOT EXISTS direct_user_id integer
    """)
    cr.execute("""
        UPDATE project_project project
           SET direct_user_id = project.user_id
         WHERE project.user_id IS NOT NULL
           AND project.direct_user_id IS NULL
           AND project.employee_id IS NULL
           AND NOT EXISTS (
                   SELECT 1
                     FROM hr_employee employee
                    WHERE employee.user_id = project.user_id
                      AND (employee.company_id = project.company_id
                           OR project.company_id IS NULL)
               )
    """)
    direct = cr.rowcount
    cr.execute("""
        UPDATE project_project project
           SET employee_id = employee.id
          FROM hr_employee employee
         WHERE employee.user_id = project.user_id
           AND (employee.company_id = project.company_id
                OR project.company_id IS NULL)
           AND project.user_id IS NOT NULL
           AND project.employee_id IS NULL
    """)
    _logger.info(
        "project_hr 1.2: %d project manager(s) kept as users without an employee, "
        "%d matched to their employee.",
        direct,
        cr.rowcount,
    )
