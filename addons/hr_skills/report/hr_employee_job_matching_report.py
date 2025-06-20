# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class HrEmployeeJobMatchingReport(models.BaseModel):
    _name = "hr.employee.job.matching.report"
    _auto = False
    _inherit = ["hr.manager.department.report"]
    _description = "Employee Job Matching Report"
    _order = "employee_id, level_progress desc"

    job_id = fields.Many2one("hr.job", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    department_id = fields.Many2one("hr.department", readonly=True)

    skill_id = fields.Many2one("hr.skill", readonly=True)
    skill_type_id = fields.Many2one("hr.skill.type", readonly=True)
    skill_level = fields.Char(readonly=True)
    level_progress = fields.Float(readonly=True, aggregator="avg")
    active = fields.Boolean(related="employee_id.active")
    target_level = fields.Float(readonly=True, aggregator="avg")  # job_id.skill.level
    job_matching = fields.Float(readonly=True, aggregator="avg")  # min(target_level * 2, level_progress) / target_level

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute(
            """
        CREATE OR REPLACE VIEW %s AS (
            SELECT
                row_number() OVER () AS id,
                e.id AS employee_id,
                v.company_id AS company_id,
                v.department_id AS department_id,
                v.job_id AS job_id,
                js.skill_id AS skill_id,
                COALESCE(s.skill_type_id, jst.id) AS skill_type_id,
                sl_emp.level_progress / 100.0 AS level_progress,
                sl_emp.name AS skill_level,
                sl_job.level_progress / 100.0 AS target_level,
                LEAST((sl_job.level_progress / 100.0) * 2, COALESCE(sl_emp.level_progress / 100.0, 0)) / COALESCE(sl_job.level_progress , 1) * 100.0 AS job_matching
            FROM hr_employee e
            INNER JOIN hr_version v on e.current_version_id = v.id
            INNER JOIN hr_job_skill js ON v.job_id = js.job_id
            INNER JOIN hr_skill_level sl_job ON sl_job.id = js.skill_level_id
            INNER JOIN hr_skill_type jst ON jst.id = sl_job.skill_type_id AND jst.active IS TRUE
            LEFT OUTER JOIN hr_employee_skill s
                ON e.id = s.employee_id
                AND js.skill_id = s.skill_id
                AND js.skill_type_id = s.skill_type_id
            LEFT OUTER JOIN hr_skill_level sl_emp
                ON sl_emp.id = s.skill_level_id
                AND sl_emp.skill_type_id = jst.id
        )
        """
            % (self._table,),
        )
