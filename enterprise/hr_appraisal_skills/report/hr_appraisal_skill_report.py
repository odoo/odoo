# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class HrAppraisalSkillReport(models.BaseModel):
    _auto = False
    _name = 'hr.appraisal.skill.report'
    _description = 'Appraisal Skills Report'
    _order = 'employee_id, evolution_sequence asc, current_level_progress desc, skill_type_id asc'

    id = fields.Id()
    display_name = fields.Char(related='employee_id.name')
    create_date = fields.Date(string='Create Date', readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    skill_id = fields.Many2one('hr.skill', readonly=True)
    skill_type_id = fields.Many2one('hr.skill.type', readonly=True)
    previous_skill_level_id = fields.Many2one('hr.skill.level', string="Previous Level", readonly=True)
    previous_level_progress = fields.Float(string="Previous Progress", readonly=True, aggregator='avg')
    current_skill_level_id = fields.Many2one('hr.skill.level', string="Current Level", readonly=True)
    current_level_progress = fields.Float(string="Current Progress", readonly=True, aggregator='avg')
    justification = fields.Char(readonly=True)
    evolution_sequence = fields.Integer()
    evolution = fields.Selection([
        ('improvement', 'Improvement'),
        ('same', 'Same'),
        ('just_added', 'Just added'),
        ('decline', 'Decline'),
    ], 'Evolution')
    progress_evolution = fields.Float("Progress Evolution", readonly=True, aggregator='avg')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
        CREATE OR REPLACE VIEW %s AS (
            SELECT
            row_number() OVER () AS id,
                e.id AS employee_id,
                date(s.create_date) as create_date,
                e.company_id AS company_id,
                e.department_id AS department_id,
                s.skill_id AS skill_id,
                s.justification AS justification,
                sl.skill_type_id AS skill_type_id,
                sl.level_progress / 100.0 AS current_level_progress,
                sl.id AS current_skill_level_id,
                sl_p.id AS previous_skill_level_id,
                sl_p.level_progress / 100.0 AS previous_level_progress,
                (sl.level_progress - sl_p.level_progress) / 100.0 AS progress_evolution,
            CASE
                WHEN sl.level_progress > sl_p.level_progress THEN 'improvement'
                WHEN sl.level_progress < sl_p.level_progress THEN 'decline'
                WHEN sl_p.level_progress is NULL THEN 'just_added'
                WHEN sl.level_progress = sl_p.level_progress THEN 'same'
            END AS evolution,
            CASE
                WHEN sl.level_progress > sl_p.level_progress THEN 1
                WHEN sl.level_progress < sl_p.level_progress THEN 3
                WHEN sl_p.level_progress is NULL THEN 2
                WHEN sl.level_progress = sl_p.level_progress THEN 4
            END AS evolution_sequence
            FROM hr_employee e
            JOIN hr_appraisal_skill s ON e.id = s.employee_id
            JOIN hr_skill_level sl ON sl.id = s.skill_level_id
            LEFT JOIN hr_skill_level sl_p ON sl_p.id = s.previous_skill_level_id
            JOIN hr_appraisal a ON a.id = s.appraisal_id
            JOIN hr_skill_type st ON st.id = s.skill_type_id
            WHERE a.id = (
                SELECT a2.id FROM hr_appraisal a2
                WHERE a2.employee_id = e.id AND e.active IS TRUE AND a2.state = 'done'
                ORDER BY a2.create_date desc limit 1
            ) and st.active IS True
        )
        """ % (self._table))
