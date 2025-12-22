# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools

class HrEmployeeSkillReport(models.BaseModel):
    _auto = False
    _name = 'hr.employee.skill.report'
    _inherit = "hr.manager.department.report"
    _description = 'Employee Skills Report'
    _order = 'employee_id, level_progress desc'

    id = fields.Id()
    display_name = fields.Char(related='employee_id.name')
    company_id = fields.Many2one('res.company', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)

    skill_id = fields.Many2one('hr.skill', readonly=True)
    skill_type_id = fields.Many2one('hr.skill.type', readonly=True)
    skill_level = fields.Char(readonly=True)
    level_progress = fields.Float(readonly=True, aggregator='avg')
    active = fields.Boolean(related='employee_id.active')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
        CREATE OR REPLACE VIEW %s AS (
            SELECT
                row_number() OVER () AS id,
                e.id AS employee_id,
                e.company_id AS company_id,
                e.department_id AS department_id,
                s.skill_id AS skill_id,
                s.skill_type_id AS skill_type_id,
                sl.level_progress / 100.0 AS level_progress,
                sl.name AS skill_level
            FROM hr_employee e
            LEFT OUTER JOIN hr_employee_skill s ON e.id = s.employee_id
            LEFT OUTER JOIN hr_skill_level sl ON sl.id = s.skill_level_id
            LEFT OUTER JOIN hr_skill_type st ON st.id = sl.skill_type_id
            WHERE st.active IS True
        )
        """ % (self._table, ))
