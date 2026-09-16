import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Keep every project manager the database already has.

    `project.project.user_id` is composed here from `employee_id.user_id`, and
    gains `direct_user_id` in this version for a manager who holds no employee
    record. Adding that dependency makes the ORM recompute the field for every
    row, which would answer an empty employee with an empty manager -- and the
    managers that answer describes are the majority: on the production database
    read for this migration, 41 of 42 projects are managed by someone with no
    employee in the project's company.

    Their user is still in the column, because the compute has never been
    triggered on those rows. This runs before the recompute and puts each one
    where the new compute will find it, so the manager a project has today is the
    manager it has tomorrow.
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
