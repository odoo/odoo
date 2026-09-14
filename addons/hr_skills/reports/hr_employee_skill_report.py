from odoo import api, fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.tools import SQL


class HrEmployeeSkillReport(models.BaseModel):
    _name = "hr.employee.skill.report"
    _auto = False
    _inherit = ["mixin.hr.manager.department.report"]
    _description = "Employee Skills Report"
    _order = "employee_id, level_progress desc"

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        readonly=True,
    )
    job_id = fields.Many2one(
        comodel_name="hr.job",
        readonly=True,
    )

    skill_id = fields.Many2one(
        comodel_name="hr.skill",
        readonly=True,
    )
    skill_type_id = fields.Many2one(
        comodel_name="hr.skill.type",
        readonly=True,
    )
    skill_level = fields.Char(readonly=True)
    level_progress = fields.Float(
        readonly=True,
        aggregator="avg",
    )
    active = fields.Boolean(readonly=True)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute(
            SQL(
                """
        CREATE OR REPLACE VIEW %s AS (
            SELECT
                s.id AS id,
                e.id AS employee_id,
                e.company_id AS company_id,
                v.department_id AS department_id,
                v.job_id AS job_id,
                s.skill_id AS skill_id,
                s.skill_type_id AS skill_type_id,
                sl.level_progress / 100.0 AS level_progress,
                sl.name AS skill_level,
                e.active AS active
            FROM hr_employee_skill s
            JOIN hr_employee e ON e.id = s.employee_id
            JOIN hr_skill_level sl ON sl.id = s.skill_level_id
            JOIN hr_skill_type st ON st.id = sl.skill_type_id
            LEFT JOIN hr_version v ON v.id = e.current_version_id
            WHERE st.active AND st.is_certification IS NOT TRUE
              AND s.valid_from <= (now() AT TIME ZONE 'UTC')::date
              AND (s.valid_to IS NULL OR s.valid_to >= (now() AT TIME ZONE 'UTC')::date)
        )
        """,
                SQL.identifier(self._table),
            )
        )

    @api.model
    def formatted_read_grouping_sets(
        self, domain, grouping_sets, aggregates=(), *, order=None
    ):
        self_contexted = self.with_context(hierarchical_naming=False)
        return super(
            HrEmployeeSkillReport, self_contexted
        ).formatted_read_grouping_sets(
            domain,
            grouping_sets,
            aggregates,
            order=order,
        )
