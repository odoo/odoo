# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class HrAttendanceBreakRule(models.Model):
    """Minimum break of an attendance, by the hours of the attendance.

    The rule applies to the employees of its company (all companies if empty) matching ``employee_domain``. When
    several rules match an employee, the first one by sequence applies. An attendance longer than the hours of a line
    (``check_out - check_in``) gets at least the break of that line, see ``hr.attendance._get_break_rule_raises``.
    Each attendance counts on its own, not the whole day.
    """
    _name = 'hr.attendance.break.rule'
    _description = "Attendance Break Rule"
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company')
    employee_domain = fields.Char(
        string="Employees",
        default='[]',
        help="The rule applies to the attendances of the matching employees.",
    )
    line_ids = fields.One2many('hr.attendance.break.rule.line', 'rule_id', string="Breaks", copy=True)

    @api.constrains('employee_domain')
    def _check_employee_domain(self):
        for rule in self:
            try:
                literal_eval(rule.employee_domain or '[]')
            except Exception as e:  # noqa: BLE001
                raise ValidationError(self.env._(
                    "Break rule '%(name)s': invalid employee domain %(domain)s",
                    name=rule.name,
                    domain=rule.employee_domain,
                )) from e

    @api.model
    def _get_rule_by_employee(self, employees):
        """Return the break rule of each employee: the first rule by sequence of their company whose employee domain
        matches them.

        :param employees: ``hr.employee`` recordset
        :return: ``{employee: hr.attendance.break.rule}``, only the employees with a rule
        :rtype: dict
        """
        result = {}
        remaining = employees.sudo()
        # sudo: the employees checking in and out may not read the rules
        rules = self.sudo().search([('company_id', 'in', employees.company_id.ids + [False])])
        for rule in rules:
            if not remaining:
                break
            matching = remaining.filtered(lambda e: not rule.company_id or e.company_id == rule.company_id)
            matching = matching.filtered_domain(literal_eval(rule.employee_domain or '[]'))
            result.update(dict.fromkeys(matching, rule))
            remaining -= matching
        return result

    def _get_line(self, hours):
        """Return the line with the highest hours that ``hours`` exceed.

        :param float hours: duration of the attendance
        :rtype: hr.attendance.break.rule.line
        """
        self.ensure_one()
        return self.line_ids.filtered(
            lambda line: float_compare(hours, line.work_hours, precision_digits=4) > 0,
        ).sorted('work_hours')[-1:]


class HrAttendanceBreakRuleLine(models.Model):
    _name = 'hr.attendance.break.rule.line'
    _description = "Attendance Break Rule Line"
    _order = 'work_hours, id'

    rule_id = fields.Many2one('hr.attendance.break.rule', required=True, index=True, ondelete='cascade')
    work_hours = fields.Float(string="Attendance Longer Than", required=True)
    break_hours = fields.Float(string="Minimum Break", required=True)

    _break_hours_valid = models.Constraint(
        'CHECK(0 < break_hours AND break_hours <= work_hours)',
        "The minimum break must be positive and not longer than the attendance hours of its line.",
    )
