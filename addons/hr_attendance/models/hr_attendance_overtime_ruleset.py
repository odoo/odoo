# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo import api

MONTHS_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


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
    max_positive_hours = fields.Float(
        string="Maximum Positive Hours",
        default=0.0,
        help="Maximum number of hours per month that will be counted as positive hours. "
             "Hours above this limit will not be counted. Set to 0 for unlimited.",
    )
    max_negative_hours = fields.Float(
        string="Maximum Negative Hours",
        default=0.0,
        help="Maximum negative hours (undertime) per month allowed without salary deduction. "
             "Employee keeps full salary if negative hours are within this limit. Set to 0 for unlimited.",
    )
    l10n_be_flexibility_type = fields.Selection([
        ('none', 'None'),
        ('small_flexibility', 'Small Flexibility'),
        ('floating', 'Floating Hours'),
    ], string="Flexibility Type", default='none',
        help="Select the applicable regime: 'Small Flexibility' for employer-planned high/low cycles "
             "(constant salary), or 'Floating Hours' for employee autonomy within core hours "
             "(subject to potential salary deductions).")

    l10n_be_flexibility_reference_month = fields.Selection(
        MONTHS_SELECTION,
        string="Reference Month",
        default='1',
        help="The month marking the start of the reference period for Small Flexibility.")

    l10n_be_flexibility_reference_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ], string="Reference Period", default='quarterly',
        help="The period at the end of which the flexibility balance is evaluated.")
    rules_count = fields.Integer(compute='_compute_rules_count')
    active = fields.Boolean(default=True, readonly=False)
    version_ids = fields.One2many('hr.version', 'ruleset_id')
    versions_count = fields.Integer(compute="_compute_versions_count")

    def _get_current_versions_domain(self):
        today = fields.Date.today()
        return [
            ("ruleset_id", "in", self.ids),
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
        count_by_ruleset = dict(self.env['hr.version']._read_group(
                domain=self._get_current_versions_domain(),
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
        elligible_attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', elligible_version.employee_id.ids),
            ('date', '>=', min(elligible_version.mapped('date_version'))),
        ])
        return elligible_attendances

    def action_regenerate_overtimes(self):
        self._attendances_to_regenerate_for()._update_overtime()

    def action_show_versions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_version_list_view')
        action['domain'] = self._get_current_versions_domain()
        action['context'] = {'default_ruleset_id': self.id}
        return action

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", ruleset.name)) for ruleset, vals in zip(self, vals_list)]

    # @api.onchange('l10n_be_flexibility_type')
    # def _onchange_l10n_be_flexibility_type(self):
    #     if self.l10n_be_flexibility_type == 'small_flexibility':
    #         self.absence_management = True
