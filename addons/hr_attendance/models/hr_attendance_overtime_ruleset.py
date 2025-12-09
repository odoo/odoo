# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from collections import defaultdict


class HrAttendanceOvertimeRuleset(models.Model):
    _name = 'hr.attendance.overtime.ruleset'
    _description = "Overtime Ruleset"

    name = fields.Char(required=True)
    description = fields.Html()
    rule_ids = fields.One2many('hr.attendance.overtime.rule', 'ruleset_id', copy=True)
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    country_id = fields.Many2one(
        'res.country',
        default=lambda self: self.env.company.country_id,
        domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)],
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
    version_ids = fields.One2many('hr.version', 'ruleset_id')
    versions_count = fields.Integer(compute="_compute_versions_count")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name", False):
                vals['name'] = self.env._("Unnamed Ruleset")
        return super().create(vals_list)

    def _get_current_versions_domain(self):
        today = fields.Date.today()
        return [
            ("date_version", "<=", today),
            ("contract_date_start", "<=", today),
            "|",
                ("contract_date_end", "=", False),
                ("contract_date_end", ">=", today),
            ('employee_id', '!=', False),
        ]

    def _compute_rules_count(self):
        for ruleset in self:
            ruleset.rules_count = len(ruleset.rule_ids)

    def _compute_versions_count(self):
        versions = self.env['hr.version']._read_group(
            domain=self._get_current_versions_domain(),
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        )
        count_by_ruleset = defaultdict(int)
        for employee, recordset in versions:
            record = recordset.sorted('date_version DESC')[0]
            if record.ruleset_id in self:
                count_by_ruleset[record.ruleset_id] += 1
        for ruleset in self:
            ruleset.versions_count = count_by_ruleset.get(ruleset, 0)

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

    def action_show_versions(self):
        self.ensure_one()
        data = self.env['hr.version']._read_group(
            domain=self._get_current_versions_domain(),
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        )
        versions = self.env['hr.version']
        for employee, recordset in data:
            record = recordset.sorted('date_version DESC')[0]
            versions |= record
        action = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_version_list_view')
        action['domain'] = [('id', 'in', versions.ids)]
        action['context'] = {
            'search_default_ruleset_id': self.id,
            'default_ruleset_id': self.id,
        }
        return action

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", ruleset.name)) for ruleset, vals in zip(self, vals_list)]

    def action_create_overtime_rule(self):
        return {
            'name': self.env._('Create Rule'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.overtime.rule',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'view_id': self.env.ref('hr_attendance.hr_attendance_overtime_rule_view_form').id,
            'target': 'new',
        }
