# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
    l10n_au_leave_loading_rate = fields.Float(string="Leave Loading Rate")
    l10n_au_employment_basis_code = fields.Selection(
        selection=[
            ("F", "(F) Full time"),
            ("P", "(P) Part time"),
            ("C", "(C) Casual"),
            ("L", "(L) Labour hire"),
            ("V", "(V) Voluntary agreement"),
            ("D", "(D) Death beneficiary"),
            ("N", "(N) Non-employee")],
        string="Employment Basis Code",
        default="F",
        required=True,
        compute="_compute_l10n_au_employment_basis_code",
        readonly=False,
        store=True)
    l10n_au_tax_treatment_category = fields.Selection(
        related="structure_type_id.l10n_au_tax_treatment_category")
    l10n_au_tax_treatment_option = fields.Selection(
        [
            ("T", "(T) Tax-free Threshold"),
            ("N", "(N) No Tax-free Threshold"),
            ("D", "(D) Daily Work Pattern"),
            ("P", "(P) Promotional Program"),
            ("F", "(F) Foreign Resident"),
            ("A", "(A) Australian Resident"),
            ("R", "(R) Registered"),
            ("U", "(U) Unregistered"),
            ("C", "(C) Commissioner's Instalment Rate"),
            ("O", "(O) Other Rate"),
            ("S", "(S) Single"),
            ("M", "(M) Married"),
            ("I", "(I) Illness-separated"),
            ("V", "(V) Downward Variation"),
            ("B", "(B) Death Beneficiary"),
            ("Z", "(Z) Non-employee"),
        ],
        default="T", required=True, compute="_compute_l10n_au_tax_treatment_option",
        readonly=False, string="Tax Treatment Option")
    l10n_au_tax_treatment_code = fields.Char(string="Tax Treatment Code", store=True,
        compute="_compute_l10n_au_tax_treatment_code")
    l10n_au_cessation_type_code = fields.Selection(
        [
            ("V", "(V) Voluntary Cessation"),
            ("I", "(I) Ill Health"),
            ("D", "(D) Deceased"),
            ("R", "(R) Redundancy"),
            ("F", "(F) Dismissal"),
            ("C", "(C) Contract Cessation"),
            ("T", "(T) Transfer"),
        ],
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
    l10n_au_withholding_variation = fields.Boolean(string="Withholding Variation", help="Employee has a custom withholding rate.")
    l10n_au_withholding_variation_amount = fields.Float(string="Withholding Variation rate")
    l10n_au_performances_per_week = fields.Integer(string="Performances per week")
    l10n_au_income_stream_type = fields.Selection(related="structure_type_id.l10n_au_income_stream_type", readonly=False)
    l10n_au_country_code = fields.Many2one("res.country", string="Country", help="Country where the work is performed")
    l10n_au_workplace_giving = fields.Float(string="Workplace Giving")
    l10n_au_salary_sacrifice_superannuation = fields.Float(string="Salary Sacrifice Superannuation")
    l10n_au_salary_sacrifice_other = fields.Float(string="Salary Sacrifice Other")
    l10n_au_yearly_wage = fields.Monetary(string="Yearly Wage", compute="_compute_wages", inverse="_inverse_yearly_wages", readonly=False, store=True)
    wage = fields.Monetary(compute="_compute_wages", readonly=False, store=True)
    hourly_wage = fields.Monetary(compute="_compute_wages", readonly=False, store=True)

    _sql_constraints = [(
        "l10n_au_casual_loading_span",
        "CHECK(l10n_au_casual_loading >= 0 AND l10n_au_casual_loading <= 100)",
        "The casual loading is a percentage and should have a value between 0 and 100."
    )]

    @api.constrains('employee_id', 'schedule_pay')
    def _check_l10n_au_schedule_pay(self):
        allowed_schedule_pay = ('daily', 'weekly', 'bi-weekly', 'monthly', 'quarterly')
        for contract in self:
            if contract.country_code == 'AU' and contract.schedule_pay not in allowed_schedule_pay:
                raise UserError(_('Australian contracts are only supported for daily, weekly, fortnightly, monthly and quarterly pay schedules.'))

    @api.depends('wage_type')
    def _compute_l10n_au_employment_basis_code(self):
        for contract in self:
            contract.l10n_au_employment_basis_code = "C" if contract.wage_type == "hourly" else "F"

    @api.depends("l10n_au_tax_treatment_category", "employee_id", "employee_id.l10n_au_tax_free_threshold", "employee_id.is_non_resident", "employee_id.marital")
    def _compute_l10n_au_tax_treatment_option(self):
        for contract in self:
            if contract.l10n_au_tax_treatment_category in ("R", "A"):
                contract.l10n_au_tax_treatment_option = "T" if contract.employee_id.l10n_au_tax_free_threshold else "N"
            elif contract.l10n_au_tax_treatment_category == "C":
                contract.l10n_au_tax_treatment_option = "F" if contract.employee_id.is_non_resident else "T"
            elif contract.l10n_au_tax_treatment_category == "S":
                contract.l10n_au_tax_treatment_option = "M" if contract.employee_id.marital in ("married", "cohabitant") else "S"
            elif contract.l10n_au_tax_treatment_category == "H":
                contract.l10n_au_tax_treatment_option = "F" if contract.employee_id.is_non_resident else "R"
            elif contract.l10n_au_tax_treatment_category == "N":
                contract.l10n_au_tax_treatment_option = "F" if contract.employee_id.is_non_resident else "A"
            elif contract.l10n_au_tax_treatment_category == "D":
                contract.l10n_au_tax_treatment_option = "V" if contract.l10n_au_withholding_variation else "B"

    @api.depends(
        "l10n_au_tax_treatment_category", "l10n_au_tax_treatment_option",
        "employee_id.l10n_au_training_loan",
        "employee_id.l10n_au_medicare_exemption",
        "employee_id.l10n_au_medicare_surcharge",
        "employee_id.l10n_au_medicare_reduction")
    def _compute_l10n_au_tax_treatment_code(self):
        for contract in self:
            contract.l10n_au_tax_treatment_code = (contract.l10n_au_tax_treatment_category or "") \
                + (contract.l10n_au_tax_treatment_option or "") \
                + (("S" if contract.employee_id.l10n_au_training_loan else "X")) \
                + (contract.employee_id.l10n_au_medicare_exemption or "") \
                + (contract.employee_id.l10n_au_medicare_surcharge or "") \
                + (contract.employee_id.l10n_au_medicare_reduction or "")

    @api.depends("wage_type", "wage", "hourly_wage")
    def _compute_wages(self):
        for contract in self:
            if contract.country_code != "AU":
                continue
            hours_per_day = contract.resource_calendar_id.hours_per_day
            # YTI TODO Clean that brol
            _l10n_au_convert_amount = self.env['hr.payslip']._l10n_au_convert_amount
            if contract.wage_type == "hourly":
                contract.wage = _l10n_au_convert_amount(contract.hourly_wage * hours_per_day, "daily", contract.schedule_pay)
                contract.l10n_au_yearly_wage = _l10n_au_convert_amount(contract.hourly_wage * hours_per_day, "daily", "yearly")
            else:
                contract.hourly_wage = _l10n_au_convert_amount(contract.wage, contract.schedule_pay, "daily") / hours_per_day
                contract.l10n_au_yearly_wage = _l10n_au_convert_amount(contract.wage, contract.schedule_pay, "yearly")

    def _inverse_yearly_wages(self):
        if self.country_code != "AU":
            return
        hours_per_day = self.resource_calendar_id.hours_per_day
        # YTI TODO Clean that brol
        _l10n_au_convert_amount = self.env['hr.payslip']._l10n_au_convert_amount
        self.wage = _l10n_au_convert_amount(self.l10n_au_yearly_wage, "yearly", self.schedule_pay)
        self.hourly_wage = _l10n_au_convert_amount(self.l10n_au_yearly_wage, "yearly", "daily") / hours_per_day

    def get_hourly_wages(self):
        self.ensure_one()
        return {
            "overtime": self.hourly_wage * (1.25 + self.l10n_au_casual_loading / 100),
            "saturday": self.hourly_wage * (1.50 + self.l10n_au_casual_loading / 100),
            "sunday": self.hourly_wage * (1.75 + self.l10n_au_casual_loading / 100),
            "public_holiday": self.hourly_wage * (2.5 + self.l10n_au_casual_loading / 100),
        }
