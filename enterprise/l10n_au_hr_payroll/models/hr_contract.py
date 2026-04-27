# Part of Odoo. See LICENSE file for full copyright and licensing details.
from math import ceil

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

OVERTIME_CASUAL_LOADING_COEF = 1.25
SATURDAY_CASUAL_LOADING_COEF = 1.50
SUNDAY_CASUAL_LOADING_COEF = 1.75
PUBLIC_HOLIDAY_CASUAL_LOADING_COEF = 2.5

CESSATION_TYPE_CODE = [
    ("V", "(V) Voluntary Cessation"),
    ("I", "(I) Ill Health"),
    ("D", "(D) Deceased"),
    ("R", "(R) Redundancy"),
    ("F", "(F) Dismissal"),
    ("C", "(C) Contract Cessation"),
    ("T", "(T) Transfer"),
]


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_au_casual_loading = fields.Float(string="Casual Loading")
    l10n_au_pay_day = fields.Selection(
        selection=[
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday")],
        string="Regular Pay Day")
    l10n_au_eligible_for_leave_loading = fields.Boolean(string="Eligible for Leave Loading")
    l10n_au_leave_loading = fields.Selection(
        selection=[
            ("regular", "Regular"),
            ("once", "Lump Sum")],
        string="Leave Loading",
        help="How leave loading, if any, is to be paid. If Lump Sum is selected, leave loading will not be added to regular payslips automatically")
    l10n_au_leave_loading_leave_types = fields.Many2many(
        "hr.leave.type",
        string="Leave Types for Leave Loading",
        help="Leave Types that should be taken into account for leave loading, both regular and lump sum.")
    l10n_au_leave_loading_rate = fields.Float(string="Leave Loading Rate (%)")
    l10n_au_tax_treatment_category = fields.Selection(related="employee_id.l10n_au_tax_treatment_category", string="Tax Treatment Category")
    l10n_au_cessation_type_code = fields.Selection(
        CESSATION_TYPE_CODE,
        string="Cessation Type",
        help="""
            "V": an employee resignation, retirement, domestic or pressing necessity or abandonment of employment.
            "I": an employee resignation due to medical condition that prevents the continuation of employment, such as for illness, ill-health, medical unfitness or total permanent disability.
            "D": the death of an employee.
            "R": an employer-initiated termination of employment due to a genuine bona-fide redundancy or approved early retirement scheme.
            "F": an employer-initiated termination of employment due to dismissal, inability to perform the required work, misconduct or inefficiency.
            "C": the natural conclusion of a limited employment relationship due to contract/engagement duration or task completion, seasonal work completion, or to cease casuals that are no longer required.
            "T": the administrative arrangements performed to transfer employees across payroll systems, move them temporarily to another employer (machinery of government for public servants), transfer of business, move them to outsourcing arrangements or other such technical activities.
        """)
    l10n_au_performances_per_week = fields.Integer(string="Performances per week")
    l10n_au_workplace_giving = fields.Float(string="Workplace Giving Employee")
    l10n_au_workplace_giving_employer = fields.Float(string="Salary Sacrificed Workplace Giving")
    l10n_au_salary_sacrifice_superannuation = fields.Float(string="Salary Sacrifice Superannuation")
    l10n_au_salary_sacrifice_other = fields.Float(string="Salary Sacrifice Other Benefits")
    l10n_au_extra_negotiated_super = fields.Float(string="Extra Negotiated Super %",
        help="This is an additional Super Contribution negotiated by the employee. Paid by employer. (RESC)")
    l10n_au_extra_compulsory_super = fields.Float(string="Extra Compulsory Super %",
        help="This is an additional Compulsory Super Contribution required by the fund or territory law. (Not RESC)")
    l10n_au_yearly_wage = fields.Monetary(string="Yearly Wage", compute="_compute_yearly_wage", inverse="_inverse_yearly_wages", readonly=False, store=True)
    wage = fields.Monetary(compute="_compute_wage", readonly=False, store=True)
    hourly_wage = fields.Monetary(compute="_compute_hourly_wage", readonly=False, store=True)

    _sql_constraints = [(
        "l10n_au_casual_loading_span",
        "CHECK(l10n_au_casual_loading >= 0 AND l10n_au_casual_loading <= 1)",
        "The casual loading is a percentage and should have a value between 0 and 100."
    ), (
        "l10n_au_extra_negotiated_super_span",
        "CHECK(l10n_au_extra_negotiated_super >= 0 AND l10n_au_extra_negotiated_super <= 1)",
        "The Extra Negotiated super is a percentage and should have a value between 0 and 100.",
    ), (
        "l10n_au_extra_compulsory_super_span",
        "CHECK(l10n_au_extra_compulsory_super >= 0 AND l10n_au_extra_compulsory_super <= 1)",
        "The Extra Compulsory super is a percentage and should have a value between 0 and 100.",
    )]

    @api.constrains('employee_id', 'schedule_pay')
    def _check_l10n_au_schedule_pay(self):
        allowed_schedule_pay = ('daily', 'weekly', 'bi-weekly', 'monthly', 'quarterly')
        for contract in self:
            if contract.country_code == 'AU' and contract.schedule_pay not in allowed_schedule_pay:
                raise UserError(_('Australian contracts are only supported for daily, weekly, fortnightly, monthly and quarterly pay schedules.'))

    @api.depends("wage_type", "hourly_wage", "schedule_pay")
    def _compute_wage(self):
        Payslip = self.env['hr.payslip']
        for contract in self:
            if contract.country_code != "AU" or contract.wage_type != "hourly":
                continue
            daily_wage = contract.hourly_wage * contract.resource_calendar_id.hours_per_day
            contract.wage = Payslip._l10n_au_convert_amount(daily_wage, "daily", contract.schedule_pay)

    @api.depends("wage_type", "wage")
    def _compute_hourly_wage(self):
        Payslip = self.env['hr.payslip']
        for contract in self:
            if contract.country_code != "AU" or contract.wage_type == "hourly":
                continue
            hours_per_day = contract.resource_calendar_id.hours_per_day
            if not hours_per_day:
                contract.hourly_wage = 0.0
                continue
            daily_wage = Payslip._l10n_au_convert_amount(contract.wage, contract.schedule_pay, "daily")
            contract.hourly_wage = daily_wage / hours_per_day

    @api.depends("wage_type", "wage", "hourly_wage")
    def _compute_yearly_wage(self):
        Payslip = self.env['hr.payslip']
        for contract in self:
            if contract.country_code != "AU":
                continue
            hours_per_day = contract.resource_calendar_id.hours_per_day
            if contract.wage_type == "hourly":
                contract.l10n_au_yearly_wage = Payslip._l10n_au_convert_amount(contract.hourly_wage * hours_per_day, "daily", "annually")
            else:
                contract.l10n_au_yearly_wage = Payslip._l10n_au_convert_amount(contract.wage, contract.schedule_pay, "annually")

    def _inverse_yearly_wages(self):
        if self.country_code != "AU":
            return
        hours_per_day = self.resource_calendar_id.hours_per_day
        self.wage = self.env['hr.payslip']._l10n_au_convert_amount(self.l10n_au_yearly_wage, "annually", self.schedule_pay)
        if not hours_per_day:
            self.hourly_wage = 0.0
            return
        self.hourly_wage = self.env['hr.payslip']._l10n_au_convert_amount(self.l10n_au_yearly_wage, "annually", "daily") / hours_per_day

    def get_hourly_wages(self):
        self.ensure_one()
        return {
            "overtime": self.hourly_wage * (OVERTIME_CASUAL_LOADING_COEF + self.l10n_au_casual_loading),
            "saturday": self.hourly_wage * (SATURDAY_CASUAL_LOADING_COEF + self.l10n_au_casual_loading),
            "sunday": self.hourly_wage * (SUNDAY_CASUAL_LOADING_COEF + self.l10n_au_casual_loading),
            "public_holiday": self.hourly_wage * (PUBLIC_HOLIDAY_CASUAL_LOADING_COEF + self.l10n_au_casual_loading),
        }

    @api.model
    def _l10n_au_get_financial_year_start(self, date):
        if date.month < 7:
            return date + relativedelta(years=-1, month=7, day=1)
        return date + relativedelta(month=7, day=1)

    @api.model
    def _l10n_au_get_financial_year_end(self, date):
        if date.month < 7:
            return date + relativedelta(month=6, day=30)
        return date + relativedelta(years=1, month=6, day=30)

    @api.model
    def _l10n_au_get_weeks_amount(self, date=False):
        """ Returns the amount of pay weeks in the current financial year.
        In leap years, there will be an additional week/fortnight.
        """
        target_day = date or fields.Date.context_today(self)
        start_day = self._l10n_au_get_financial_year_start(target_day)
        end_day = self._l10n_au_get_financial_year_end(target_day) + relativedelta(day=30)
        return ceil((end_day - start_day).days / 7)
