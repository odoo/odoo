# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertimeRuleset(models.Model):
    _name = 'hr.attendance.overtime.ruleset'
    _description = "Overtime Ruleset"

    name = fields.Char(required=True)
    description = fields.Html()
    rule_ids = fields.One2many('hr.attendance.overtime.rule', 'ruleset_id')
    version_ids = fields.One2many('hr.version', 'ruleset_id')
    country_id = fields.Many2one(
        'res.country',
        default=lambda self: self.env.company.country_id,
    )
    rate_combination_mode = fields.Selection([
            ('max', "Max"),
            ('sum', "Sum"),
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
    active = fields.Boolean(default=True, store=True, readonly=False)

    def _compute_rules_count(self):
        for ruleset in self:
            ruleset.rules_count = len(ruleset.rule_ids)

    def _attendances_to_regenerate_for(self):
        if not self.version_ids:
            return self.env['hr.attendance']
        attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', self.version_ids.employee_id.ids),
            ('date', '>=', min(self.version_ids.mapped('date_version'))),
        ])
        return self.env['hr.attendance'].search([
            ('employee_id', 'in', self.version_ids.employee_id.ids),
            ('date', '>=', min(self.version_ids.mapped('date_version'))),
        ])

    def action_regenerate_overtimes(self):
        self._attendances_to_regenerate_for()._update_overtime()
