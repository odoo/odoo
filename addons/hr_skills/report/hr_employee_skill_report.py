# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools

class HrEmployeeSkillReport(models.BaseModel):
    _auto = False
    _name = 'hr.employee.skill.report'
    _description = 'Employee Skills Report'
    _order = 'employee_id, level_progress desc'

    id = fields.Id()
    display_name = fields.Char(related='employee_id.name')
    employee_id = fields.Many2one('hr.employee', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)

    skill_id = fields.Many2one('hr.skill', readonly=True)
    skill_type_id = fields.Many2one('hr.skill.type', readonly=True)
    skill_level = fields.Char(readonly=True)
    level_progress = fields.Float(readonly=True, group_operator='avg')

    def _select_skill(self, fields=None):
        if not fields:
            fields = {}
        select_ = """
                row_number() OVER () AS id,
                e.id AS employee_id,
                e.company_id AS company_id,
                e.department_id AS department_id,
                s.skill_id AS skill_id,
                s.skill_type_id AS skill_type_id,
                sl.level_progress / 100.0 AS level_progress,
                sl.name AS skill_level"""
        for field in fields.values():
            select_ += field
        return select_

    def _from_skill(self, from_clause=''):
        from_ = """
            hr_employee e
                LEFT OUTER JOIN hr_employee_skill s ON e.id = s.employee_id
                LEFT OUTER JOIN hr_skill_level sl ON sl.id = s.skill_level_id
                %s
        """ % from_clause
        return from_

    def _select_additional_fields(self, fields):
        """Hook to return additional fields SQL specification for select part of the table query.
        :param dict fields: additional fields info provided by _query overrides (old API), prefer overriding
            _select_additional_fields instead.
        :returns: mapping field -> SQL computation of the field
        :rtype: dict
        """
        return fields

    def _query(self, with_clause='', fields=None, from_clause=''):
        if not fields:
            fields = {}
        skill_report_fields = self._select_additional_fields(fields)
        with_ = ("WITH %s" % with_clause) if with_clause else ""
        return '%s (SELECT %s FROM %s)' % \
               (with_, self._select_skill(skill_report_fields), self._from_skill(from_clause))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (%s)""" % (self._table, self._query()))
