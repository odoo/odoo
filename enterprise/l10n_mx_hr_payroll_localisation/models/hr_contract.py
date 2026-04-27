# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_mx_schedule_pay_temp = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('10_days', '10 Days'),
        ('14_days', '14 Days'),
        ('bi_weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('bi_monthly', 'Bi-monthly'),
    ], compute='_compute_l10n_mx_schedule_pay', store=True, readonly=False, required=True,
        string="MX: Schedule Pay (Temp)", default="monthly", index=True)

    l10n_mx_payment_period_vouchers = fields.Selection([
        ('last_day_of_month', 'Last Day of the Month'),
        ('in_period', 'In the period'),
    ], default="last_day_of_month", required=True)
    l10n_mx_meal_voucher_amount = fields.Monetary(string="MX: Meal Vouchers")
    l10n_mx_transport_amount = fields.Monetary(string="MX: Transport Amount")
    l10n_mx_gasoline_amount = fields.Monetary(string="MX: Gasoline Amount")

    l10n_mx_savings_fund = fields.Monetary(string="MX: Savings Fund")
    l10n_mx_infonavit = fields.One2many(
        'l10n.mx.hr.infonavit', 'contract_id', string="MX: Infonavit",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_mx_fonacot = fields.One2many(
        'l10n.mx.hr.fonacot', 'contract_id', string="MX: Fonacot",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_mx_external_annual_declaration = fields.Boolean(
        string="MX: External Annual Declaration",
        help="Activate this box if the employee will make the annual tax return on their own. "
             "By activating it, the annual ISR adjustment will not be applied.")

    _sql_constraints = [
        ('christmas_bonus_rate',
         'CHECK (0 <= l10n_mx_holiday_bonus_rate AND l10n_mx_holiday_bonus_rate <= 100)',
         'The Christmas Bonus rate must be between 0 and 100'),
    ]

    @api.depends('structure_type_id')
    def _compute_l10n_mx_schedule_pay(self):
        for contract in self:
            contract.l10n_mx_schedule_pay_temp = contract.structure_type_id.l10n_mx_default_schedule_pay
