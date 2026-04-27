# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

STATES = ['NY', 'CA', 'AL', 'CO', 'VT', 'IL', 'AZ', 'DC', 'NC', 'VA', 'OR', 'ID']


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _get_selection_state_filing_status(self):
        return [
            ('ca_status_1', 'CA: Single, Dual Income Married or Married with Multiple Employers'),
            ('ca_status_2', 'CA: Married: One Income'),
            ('ca_status_4', 'CA: Unmarried Head of Household'),
            ('ny_status_1', 'NY: Single or Head of Household'),
            ('ny_status_2', 'NY: Married (filing jointly)'),
            ('ny_status_3', 'NY: Married, but withhold at a higher single rate'),
            ('al_status_1', 'AL: 0: No Exemption Made (withhold at the highest rate)'),
            ('al_status_2', 'AL: S: Single'),
            ('al_status_3', 'AL: MS: Married filing Separately'),
            ('al_status_4', 'AL: M: Married'),
            ('al_status_5', 'AL: H: Head of Household'),
            ('co_status_1', 'CO: Single or Married filing Separately'),
            ('co_status_2', 'CO: Married filing Jointly or Qualifying Surviving Spouse'),
            ('co_status_3', 'CO: Head of Household'),
            ('vt_status_1', 'VT: Single'),
            ('vt_status_2', 'VT: Married/Civil Union Filing Jointly'),
            ('vt_status_3', 'VT: Married/Civil Union Filing Separately'),
            ('vt_status_4', 'VT: Married, but withhold at a higher single rate'),
            ('il_status_1', 'IL: General rate used for deductions'),
            ('az_status_1', 'AZ: Withhold wages at 0.5%'),
            ('az_status_2', 'AZ: Withhold wages at 1.0%'),
            ('az_status_3', 'AZ: Withhold wages at 1.5%'),
            ('az_status_4', 'AZ: Withhold wages at 2.0%'),
            ('az_status_5', 'AZ: Withhold wages at 2.5%'),
            ('az_status_6', 'AZ: Withhold wages at 3.0%'),
            ('az_status_7', 'AZ: Withhold wages at 3.5%'),
            ('dc_status_1', 'DC: Single'),
            ('dc_status_2', 'DC: Married/domestic partners filing jointly/qualifying widow(er) with dependent child'),
            ('dc_status_3', 'DC: Head of household'),
            ('dc_status_4', 'DC: Married filing separately'),
            ('dc_status_5', 'DC: Married/domestic partners filing separately on same return'),
            ('nc_status_1', 'NC: Single or Married Filing Separately'),
            ('nc_status_2', 'NC: Head of Household'),
            ('nc_status_3', 'NC: Married Filing Jointly or Surviving Spouse'),
            ('va_status_1', 'VA: Single'),
            ('va_status_2', 'VA: Married, Filing a Joint Return'),
            ('va_status_3', 'VA: Married, Filing a Separate Return'),
            ('or_status_1', 'OR: Single'),
            ('or_status_2', 'OR: Married'),
            ('id_status_1', 'ID: Single'),
            ('id_status_2', 'ID: Married'),
            ('id_status_3', 'ID: Married, but withhold at Single rate'),
        ]

    l10n_us_old_w4 = fields.Boolean(
        string="Filed in 2019 or Before",
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
        selection=_get_selection_state_filing_status,
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
            if not state_code:
                continue
            if state_code not in STATES and filing_status:
                raise UserError(_('The employee state filing status should be empty for this working address state. (Work Address State: %s)', employee.address_id.state_id.name))
            if state_code not in STATES:
                continue
            if not filing_status:
                raise UserError(_('The employee state filing status is empty and should match the working address state. (Work Address State: %s)', employee.address_id.state_id.name))
            if not filing_status.startswith(state_code.lower()):
                selection_description_values = {
                    e[0]: e[1] for e in self._fields['l10n_us_state_filing_status']._description_selection(self.env)}
                raise UserError(_('The employee state filing status should match the working address state. (Filing Status: %(filing_status)s, Work Address State: %(address_state)s)', filing_status=selection_description_values[filing_status], address_state=employee.address_id.state_id.name))

    @api.depends('address_id.state_id')
    def _compute_l10n_us_state_filing_status(self):
        for employee in self:
            state_code = employee.address_id.state_id.code
            filing_status = employee.l10n_us_state_filing_status
            if not state_code or state_code not in STATES:
                employee.l10n_us_state_filing_status = False
            elif not filing_status or state_code != filing_status.split('_')[0].upper():
                if state_code == 'NY':
                    employee.l10n_us_state_filing_status = 'ny_status_1'
                elif state_code == 'CA':
                    employee.l10n_us_state_filing_status = 'ca_status_1'
                elif state_code == 'AL':
                    employee.l10n_us_state_filing_status = 'al_status_1'
                elif state_code == 'CO':
                    employee.l10n_us_state_filing_status = 'co_status_1'
                elif state_code == 'VT':
                    employee.l10n_us_state_filing_status = 'vt_status_1'
                elif state_code == 'IL':
                    employee.l10n_us_state_filing_status = 'il_status_1'
                elif state_code == 'AZ':
                    employee.l10n_us_state_filing_status = 'az_status_4'
                elif state_code == 'DC':
                    employee.l10n_us_state_filing_status = 'dc_status_1'
                elif state_code == 'NC':
                    employee.l10n_us_state_filing_status = 'nc_status_1'
                elif state_code == 'VA':
                    employee.l10n_us_state_filing_status = 'va_status_1'
                elif state_code == 'OR':
                    employee.l10n_us_state_filing_status = 'or_status_1'
                elif state_code == 'ID':
                    employee.l10n_us_state_filing_status = 'id_status_1'

    @api.constrains('ssnid')
    def _check_ssnid(self):
        super()._check_ssnid()
        for employee in self:
            if employee.company_id.country_id.code != "US":
                continue
            if employee.ssnid and (len(employee.ssnid) != 9 or not employee.ssnid.isdigit()):
                raise UserError(_('Social Security number (SSN) should be a nine-digit number.'))
