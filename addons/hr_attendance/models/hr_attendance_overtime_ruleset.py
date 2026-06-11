# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class HrAttendanceOvertimeRuleset(models.Model):
    _name = 'hr.attendance.overtime.ruleset'
    _description = "Overtime Ruleset"

    name = fields.Char(required=True)
    description = fields.Html()
    rule_ids = fields.One2many('hr.attendance.overtime.rule', 'ruleset_id', copy=True)
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company, index='btree_not_null')
    country_id = fields.Many2one(
        'res.country',
        compute='_compute_country_id',
        store=True,
        readonly=False,
        domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)],
        index='btree_not_null',
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

    @api.depends('company_id.country_id')
    def _compute_country_id(self):
        for ruleset in self:
            if ruleset.company_id:
                ruleset.country_id = ruleset.company_id.country_id
            elif not ruleset.country_id:
                ruleset.country_id = self.env.company.country_id

    def _get_versions_with_current_ruleset_domain(self):
        return Domain.AND([[("ruleset_id", "in", self.ids)], self.env["hr.version"]._get_current_versions_domain()])

    def _compute_rules_count(self):
        for ruleset in self:
            ruleset.rules_count = len(ruleset.rule_ids)

    def _compute_versions_count(self):
        count_by_ruleset = dict(self.env['hr.version']._read_group(
                domain=self._get_versions_with_current_ruleset_domain(),
                groupby=['ruleset_id'],
                aggregates=['__count'],
            ))
        for ruleset in self:
            ruleset.versions_count = count_by_ruleset.get(ruleset, 0)

    def _attendances_to_regenerate_for(self):
        self.ensure_one()
        elligible_version = self.env['hr.version'].search([('ruleset_id', '=', self.id)])
        if not elligible_version:
            return self.env['hr.attendance']
        big_domain = Domain.FALSE
        for version in elligible_version:
            version_domain = [('employee_id', '=', version.employee_id.id), ('date', '>=', version.date_start)]
            if version.date_end:
                version_domain = Domain.AND([version_domain, [('date', '<=', version.date_end)]])
            big_domain = big_domain.OR([big_domain, version_domain])
        elligible_attendances = self.env['hr.attendance'].search(big_domain)
        return elligible_attendances

    def action_regenerate_overtimes(self):
        self._attendances_to_regenerate_for()._update_overtime()

    def action_show_versions(self):
        self.ensure_one()

        ctx = {'default_ruleset_id': self.id}

        if not self.versions_count:
            action = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_version_list_view_add')
            action['domain'] = self.env["hr.version"]._get_current_versions_domain()
            action['context'] = ctx
            return action

        action = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_version_list_view')
        action['domain'] = self._get_versions_with_current_ruleset_domain()
        action['context'] = ctx
        return action

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", ruleset.name)) for ruleset, vals in zip(self, vals_list)]
