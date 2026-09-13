from odoo import fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.tools import SQL


class HrEmployeeSkillHistoryReport(models.BaseModel):
    _name = "hr.employee.skill.history.report"
    _auto = False
    _description = "Employee Skills History Report"
    _order = "date desc, employee_id"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        readonly=True,
    )
    date = fields.Date()
    skill_id = fields.Many2one(
        comodel_name="hr.skill",
        readonly=True,
    )
    skill_type_id = fields.Many2one(
        comodel_name="hr.skill.type",
        readonly=True,
    )
    level_progress = fields.Float(readonly=True)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)

        # One row per (employee, skill) on every day a skill of that employee
        # started or stopped, carrying the level held on that day. When two rows
        # of the same skill cover the day, the one that started latest wins.
        self.env.cr.execute(
            SQL(
                """
        CREATE OR REPLACE VIEW %s AS (
            WITH change_date AS (
                SELECT valid_from AS date, employee_id FROM hr_employee_skill
                UNION
                SELECT valid_to AS date, employee_id FROM hr_employee_skill
                WHERE valid_to IS NOT NULL
            )
            SELECT row_number() OVER () AS id, history.*
            FROM (
                SELECT DISTINCT ON (d.date, s.employee_id, s.skill_id)
                    d.date AS date,
                    s.employee_id,
                    e.company_id AS company_id,
                    v.department_id AS department_id,
                    s.skill_id,
                    s.skill_type_id,
                    sl.level_progress
                FROM change_date d
                JOIN hr_employee_skill s
                    ON s.employee_id = d.employee_id
                    AND s.valid_from <= d.date
                    AND (s.valid_to IS NULL OR s.valid_to >= d.date)
                JOIN hr_skill_level sl ON sl.id = s.skill_level_id
                JOIN hr_skill_type st ON st.id = s.skill_type_id AND st.active
                JOIN hr_employee e ON e.id = s.employee_id
                LEFT JOIN hr_version v ON v.id = e.current_version_id
                ORDER BY d.date, s.employee_id, s.skill_id, s.valid_from DESC
            ) AS history
        )
        """,
                SQL.identifier(self._table),
            )
        )
