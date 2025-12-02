# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertimeRuleset(models.Model):
    _name = 'hr.attendance.overtime.ruleset'
    _description = "Overtime Ruleset"

    name = fields.Char(required=True)
    description = fields.Html()
    rule_ids = fields.One2many('hr.attendance.overtime.rule', 'ruleset_id')
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    country_id = fields.Many2one(
        'res.country',
        default=lambda self: self.env.company.country_id,
    )
    rate_combination_mode = fields.Selection([
            ('max', "Maximum Rate"),
            ('sum', "Sum of all rates"),
        ],
        required=True,
        default='max',
        string="Rate Combination Mode",
        help=(
            "Controls how the rates from the different rules that apply are combined.\n"
            "  Max: use the highest rate. (e.g.: combined for 150% and 120 = 150%)\n"
            "  Sum: sum the *extra* pay (i.e. above 100%).\n"
            "    e.g.: combined rate for 150% & 120% = 100% (baseline) + (150-100)% + (120-100)% = 170%\n"
        ),
    )
    rules_count = fields.Integer(compute='_compute_rules_count')
    active = fields.Boolean(default=True, readonly=False)

    def _compute_rules_count(self):
        for ruleset in self:
            ruleset.rules_count = len(ruleset.rule_ids)

    def _attendances_to_regenerate_for(self):
        self.ensure_one()
        elligible_version = self.env['hr.version'].search([('ruleset_id', '=', self.id)])
        if not elligible_version:
            return self.env['hr.attendance']
        elligible_attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', elligible_version.employee_id.ids),
            ('date', '>=', min(elligible_version.mapped('date_version'))),
        ])
        return elligible_attendances

    def action_regenerate_overtimes(self):
        self._attendances_to_regenerate_for()._update_overtime()
