import logging

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not column_exists(cr, "project_project", "direct_user_id"):
        return
    # A project manager is an employee (decided 2026-09-20): the manager 1.2 kept
    # as a user without one is matched to that user's employee, the project's
    # company first; one whose user holds no employee anywhere loses the seat and
    # is named here, because the decision refuses such a manager from now on.
    cr.execute("""
        UPDATE project_project project
           SET employee_id = matched.id
          FROM (
                SELECT DISTINCT ON (project.id) project.id AS project_id, employee.id
                  FROM project_project project
                  JOIN hr_employee employee ON employee.user_id = project.direct_user_id
                 WHERE project.employee_id IS NULL
                   AND project.direct_user_id IS NOT NULL
                 ORDER BY project.id,
                          (employee.company_id = project.company_id) DESC NULLS LAST,
                          employee.active DESC,
                          employee.id
               ) matched
         WHERE matched.project_id = project.id
    """)
    matched = cr.rowcount
    cr.execute("""
        SELECT project.id, project.name->>'en_US', users.login
          FROM project_project project
          JOIN res_users users ON users.id = project.direct_user_id
         WHERE project.employee_id IS NULL
           AND project.direct_user_id IS NOT NULL
    """)
    for project_id, name, login in cr.fetchall():
        _logger.warning(
            "project_hr 1.4: project %s (%s) loses its manager %s, who holds no "
            "employee record.",
            project_id,
            name,
            login,
        )
    cr.execute("""
        UPDATE project_project
           SET user_id = NULL
         WHERE employee_id IS NULL
           AND direct_user_id IS NOT NULL
    """)
    cr.execute("ALTER TABLE project_project DROP COLUMN IF EXISTS direct_user_id")
    _logger.info(
        "project_hr 1.4: %d project manager(s) matched to their employee.", matched
    )
