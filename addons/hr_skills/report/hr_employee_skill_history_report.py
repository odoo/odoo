# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


# DONE
class HrEmployeeSkillReport(models.BaseModel):
    _name = 'hr.employee.skill.history.report'
    _auto = False
    _description = 'Employee Skills Report'

    employee_id = fields.Many2one('hr.employee', readonly=True)
    date = fields.Date()
    skill_id = fields.Many2one('hr.skill', readonly=True)
    skill_type_id = fields.Many2one('hr.skill.type', readonly=True)
    level_progress = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
        CREATE OR REPLACE VIEW %s AS (
            WITH
                individual_skill AS (
                    SELECT
                        valid_from,
                        valid_to,
                        employee_id,
                        skill_id
                    FROM hr_employee_skill
                    ORDER BY employee_id, skill_id, valid_from ASC
                ),
                date_table AS (
                    SELECT
                        date,
                        employee_id
                    FROM (
                        SELECT
                            valid_from as date,
                            employee_id
                        FROM individual_skill AS start
                        UNION
                        SELECT
                            valid_to as date,
                            employee_id
                        FROM individual_skill AS stop
                        WHERE stop.valid_to IS NOT NULL
                    ) AS date_table
                    ORDER BY date ASC
                )
            SELECT DISTINCT ON(date_table.date, emp_skill_level.employee_id, emp_skill_level.skill_id)
                date_table.date AS date,
                emp_skill_level.employee_id,
                emp_skill_level.skill_id,
                emp_skill_level.skill_type_id,
                emp_skill_level.level_progress
            FROM date_table
            CROSS JOIN (
                SELECT
                    emp_skill.*,
                    level.level_progress
                FROM hr_employee_skill AS emp_skill
                INNER JOIN hr_skill_level AS level
                ON emp_skill.skill_level_id = level.id
            ) AS emp_skill_level
            WHERE date_table.date >= emp_skill_level.valid_from AND date_table.employee_id = emp_skill_level.employee_id AND (emp_skill_level.valid_to IS NULL OR date_table.date <= emp_skill_level.valid_to)
            ORDER BY date_table.date, emp_skill_level.employee_id, emp_skill_level.skill_id, emp_skill_level.valid_from DESC
        )
        """ % (self._table, ))
