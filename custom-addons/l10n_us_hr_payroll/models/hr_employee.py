# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_us_old_w4 = fields.Boolean(
        string="Filled in 2019 or Before",
        groups="hr.group_hr_user",
        tracking=True,
        help="Check only if W4 was filed before 2020.")
    l10n_us_w4_step_2 = fields.Boolean(
        string="Step 2(c): Multiple Jobs or Spouse Works",
        groups="hr.group_hr_user",
        tracking=True,
        help="Check if Step 2 (c) in employee's W4 form is selected.")
    l10n_us_w4_step_3 = fields.Float(
        string="Step 3: Dependents Amount (USD)",
        groups="hr.group_hr_user",
        tracking=True,
        help="The total amount in USD from Step 3 (Dependants and Other Credits) of the W4 form.")
    l10n_us_w4_step_4a = fields.Float(
        string="Step 4(a): Other Income",
        groups="hr.group_hr_user",
        tracking=True,
        help="The total amount in USD from Step 4(a) (Other Income) of the W4 form.")
    l10n_us_w4_step_4b = fields.Float(
        string="Step 4(b): Deductions",
        groups="hr.group_hr_user",
        tracking=True,
        help="The total amount in USD from Step 4(b) (Deductions) of the W4 form.")
    l10n_us_w4_step_4c = fields.Float(
        string="Step 4(c): Withholdings",
        groups="hr.group_hr_user",
        tracking=True,
        help="For 2020 W4 Form:  The total amount in USD from Step 4(c) (Extra Withholdings).  For 2019 W4 Form:  line 6 (Additional amount to withheld).")
    l10n_us_w4_allowances_count = fields.Integer(
        string="Number of Claimed Regular Allowances",
        tracking=True,
        groups="hr.group_hr_user",
        help="Total number of allowances claimed in employee's W4 form and State's withholdings certificate.")
    l10n_us_w4_withholding_deduction_allowances = fields.Integer(
        string="Withholding Allowances for estimated deductions",
        tracking=True,
        groups="hr.group_hr_user",
        help="Number of additional withholding allowances from estimated deductions. Step 1(b) in DE 4 form (CA).")
    l10n_us_filing_status = fields.Selection(
        selection=[
            ('single', 'Single'),
            ('jointly', 'Married/RDP filing jointly'),
            ('separately', 'Married/RDP filing separately'),
            ('head', 'Head of household'),
            ('survivor', 'Qualifying surviving spouse/RDP with child')],
        string="Federal Tax Filing Status",
        default='single',
        tracking=True,
        groups="hr.group_hr_user",
        help="Filing status used for Federal income tax calculation.")
    l10n_us_state_filing_status = fields.Selection(
        selection=[
            ('ca_status_1', 'CA: Single, Dual Income Married or Married with Multiple Employers'),
            ('ca_status_2', 'CA: Married: One Income'),
            ('ca_status_4', 'CA: Unmarried Head of Household'),
            ('ny_status_1', 'NY: Single or Head of Household'),
            ('ny_status_2', 'NY: Married (filling jointly)'),
            ('ny_status_3', 'NY: Married, but withhold at a higher single rate')],
        string="State Tax Filing Status",
        compute="_compute_l10n_us_state_filing_status",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
        help="Filing status used for State income tax calculation.")
    l10n_us_statutory_employee = fields.Boolean(
        string="Statutory Employee",
        groups="hr.group_hr_user",
        help="Employees that are exempt from income tax, but subject to FICA Taxes. If checked off it will appear in box 13 of the W2 Report.")
    l10n_us_retirement_plan = fields.Boolean(
        string="Retirement Plan",
        groups="hr.group_hr_user",
        help="""Employee was an "active participant" in an employer-sponsor retirement plan. If checked off it will appear in box 13 of the W2 Report.""")
    l10n_us_third_party_sick_pay = fields.Boolean(
        string="Third-Party Sick Pay",
        groups="hr.group_hr_user",
        help="Employee received third-party sick pay benefits from a third party during the tax year. If checked off it will appear in box 13 of the W2 Report.")

    @api.constrains('l10n_us_state_filing_status', 'address_id')
    def _check_us_state_filling_status(self):
        for employee in self:
            state_code = employee.address_id.state_id.code
            filing_status = employee.l10n_us_state_filing_status
            if not state_code or state_code not in ['NY', 'CA']:
                continue
            if not filing_status:
                raise UserError(_('The employee state filing status is empty and should match the working address state. (Work Address State: %s)', employee.address_id.state_id.name))
            if not filing_status.startswith(state_code.lower()):
                selection_description_values = {
                    e[0]: e[1] for e in self._fields['l10n_us_state_filing_status']._description_selection(self.env)}
                raise UserError(_('The employee state filing status should match the working address state. (Filing Status: %s, Work Address State: %s)', selection_description_values[filing_status], employee.address_id.state_id.name))

    @api.depends('address_id.state_id')
    def _compute_l10n_us_state_filing_status(self):
        for employee in self:
            state_code = employee.address_id.state_id.code
            filing_status = employee.l10n_us_state_filing_status
            if not state_code or state_code not in ['NY', 'CA']:
                continue
            if not filing_status or state_code != filing_status.split('_')[0].upper():
                if state_code == 'NY':
                    employee.l10n_us_state_filing_status = 'ny_status_1'
                elif state_code == 'CA':
                    employee.l10n_us_state_filing_status = 'ca_status_1'

    @api.constrains('ssnid')
    def _check_ssnid(self):
        super()._check_ssnid()
        for employee in self:
            if employee.company_id.country_id.code != "US":
                continue
            if employee.ssnid and (len(employee.ssnid) != 9 or not employee.ssnid.isdigit()):
                raise UserError(_('Social Security number (SSN) should be a nine-digit number.'))
