# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class HrEmployeeCertificationReport(models.BaseModel):
    _name = 'hr.employee.certification.report'
    _auto = False
    _inherit = ["hr.manager.department.report"]
    _description = 'Employee Certification Report'
    _order = 'employee_id, level_progress desc'

    company_id = fields.Many2one('res.company', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)

    skill_id = fields.Many2one('hr.skill', readonly=True)
    skill_type_id = fields.Many2one('hr.skill.type', readonly=True)
    skill_level = fields.Char(readonly=True)
    level_progress = fields.Float(readonly=True, aggregator='avg')
    active = fields.Boolean(readonly=False)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
        CREATE OR REPLACE VIEW %(table)s AS (
            SELECT
                row_number() OVER () AS id,
                e.id AS employee_id,
                e.company_id AS company_id,
                v.department_id AS department_id,
                s.skill_id AS skill_id,
                s.skill_type_id AS skill_type_id,
                sl.level_progress / 100.0 AS level_progress,
                sl.name AS skill_level,
                (s.valid_to IS NULL OR s.valid_to >= '%(date)s') AND s.valid_from <= '%(date)s' AS active
            FROM hr_employee e
            LEFT JOIN hr_version v ON e.current_version_id = v.id
            LEFT OUTER JOIN hr_employee_skill s ON e.id = s.employee_id
            LEFT OUTER JOIN hr_skill_level sl ON sl.id = s.skill_level_id
            LEFT OUTER JOIN hr_skill_type st ON st.id = sl.skill_type_id
            WHERE e.active AND st.active IS True AND st.is_certification IS TRUE
        )
        """ % {
            'table': self._table,
            'date': fields.Date.context_today(self)
        })
