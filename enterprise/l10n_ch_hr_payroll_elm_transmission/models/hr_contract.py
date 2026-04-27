# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_contract_type_domain(self):
        if self.env.company.country_id.code == "CH":
            return [('id', 'in', self._get_allowed_contract_type_ids())]
        return []

    contract_type_id = fields.Many2one('hr.contract.type', domain=lambda self: self._get_contract_type_domain(), default=lambda self: self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryMth").id)
    wage_type = fields.Selection(selection_add=[("NoTimeConstraint", "No Time Constraint")],
                                 ondelete={"NoTimeConstraint": 'cascade'}, default="monthly")
    l10n_ch_laa_group = fields.Many2one("l10n.ch.accident.group", string="LAA Code", domain='[("insurance_id.company_id", "=", company_id)]')
    laa_solution_number = fields.Selection(selection=[
        ('0', '0 - Not insured'),
        ('1', '1 - Occupational and Non-Occupational Insured, with deductions'),
        ('2', '2 - Occupational and Non-Occupational Insured, without deductions'),
        ('3', '3 - Only Occupational Insured')], default='1')
    l10n_ch_lpp_withdrawal_reason = fields.Selection(selection=[('withdrawalCompany', "Withdrawal From Company"),
                                                                ('interruptionOfEmployment', 'Interruption Of Work'),
                                                                ('retirement', "Retirement"),
                                                                ('others', 'Others')], default="withdrawalCompany", string="Withdrawal Reason", help="""Specify here the entry in LPP reason.""")
    l10n_ch_lpp_entry_reason = fields.Selection(selection=[('interruptionOfEmployment', 'Resuming Work After an Interruption'),
                                                           ('entryCompany', 'Entry In Company'),
                                                           ('others', 'Others')], string="Entry Reason", default="entryCompany", help="""Specify here the withdrawal from LPP reason.""")
    l10n_ch_lpp_entry_valid_as_of = fields.Date("Entry Valid As Of", compute="_compute_l10n_ch_lpp_entry_valid_as_of", store=True, readonly=False, help="Please Provide the validity date of the last LPP Entry")
    l10n_ch_lpp_withdrawal_valid_as_of = fields.Date("Withdrawal Valid As Of", compute="_compute_l10n_ch_lpp_withdrawal_valid_as_of", store=True, readonly=False, help="Please Provide the validity date of the last LPP Withdrawal")
    l10n_ch_lpp_solutions = fields.Many2many('l10n.ch.lpp.insurance.line', string="LPP Codes")
    l10n_ch_lpp_mutations = fields.One2many('l10n.ch.lpp.mutation', 'contract_id')
    lpp_employee_amount = fields.Float(string="LPP Employee Contributions")
    lpp_company_amount = fields.Float(string="LPP Company Contributions")
    l10n_ch_14th_month = fields.Boolean(string="14th Month")
    irregular_working_time = fields.Boolean(string="Irregular Working Time")
    l10n_ch_weekly_hours = fields.Float(string="Weekly Hours", compute="_compute_l10n_ch_weekly_hours", store=True, readonly=False)
    l10n_ch_weekly_lessons = fields.Float(string="Weekly Lessons")
    l10n_ch_other_employers = fields.Boolean(compute="_compute_l10n_ch_other_employers", store=True)
    l10n_ch_other_employers_occupation_rate = fields.Float(compute="_compute_l10n_ch_other_employers_occupation_rate", store=True)
    l10n_ch_current_occupation_rate = fields.Float(string="Current Occupation rate", compute='_compute_l10n_ch_current_occupation_rate', inverse="_inverse_l10n_ch_current_occupation_rate", store=True, readonly=False)

    l10n_ch_contractual_holidays_rate = fields.Float(string="Holiday Compensation", compute="_compute_l10n_ch_contractual_holidays_rate", store=True, readonly=False)
    l10n_ch_contractual_public_holidays_rate = fields.Float(string="Public Holiday Compensation", compute="_compute_l10n_ch_contractual_public_holidays_rate", store=True, readonly=False)
    l10n_ch_contractual_vacation_pay = fields.Boolean(string="Pay Holiday Compensation each month", default=True, help="""If unselected, vacation pay should be paid manually the moment the employee takes his vacation.""")
    l10n_ch_contractual_annual_wage = fields.Monetary(string="Contractual Annual Wage", default=0, help="""
    
""")

    # Statistics
    l10n_ch_permanent_staff_public_admin = fields.Boolean("Permanent Staff for Public Administrations", help="""
A flag that allows for the clear identification of core personnel within public administrations. 
This flag will only be used by public administrations (municipalities, cities, districts, cantons, the Confederation, etc.) and churches. 
It will enable the distinction between core staff and various external mandates (such as exam experts, interpreters, etc.) and other engagements that are not part of the permanent workforce.
""")

    l10n_ch_interim_worker = fields.Boolean(string="Interim Worker")

    l10n_ch_contract_wage_ids = fields.One2many("l10n.ch.hr.contract.wage", "contract_id", domain=[('date_start', '=', False)], copy=True)
    one_time_wage_count = fields.Integer(compute="_compute_one_time_wage_count")

    l10n_ch_has_monthly = fields.Boolean("Has Monthly Wage")
    l10n_ch_has_hourly = fields.Boolean("Has Hourly Wage")
    l10n_ch_has_lesson = fields.Boolean("Has Lesson Wage")

    l10n_ch_additional_accident_insurance_line_ids = fields.Many2many(domain='[("insurance_id.company_id", "=", company_id)]')
    l10n_ch_sickness_insurance_line_ids = fields.Many2many(domain='[("insurance_id.company_id", "=", company_id)]')


    @api.onchange('l10n_ch_has_monthly')
    def _onchange_l10n_ch_has_monthly(self):
        if not self.l10n_ch_has_monthly:
            self.wage = 0
    @api.onchange('l10n_ch_has_hourly')
    def _onchange_l10n_ch_has_hourly(self):
        if not self.l10n_ch_has_hourly:
            self.hourly_wage = 0
    @api.onchange('l10n_ch_has_lesson')
    def _onchange_l10n_ch_has_lesson(self):
        if not self.l10n_ch_has_lesson:
            self.l10n_ch_lesson_wage = 0


    def _get_allowed_contract_type_ids(self):
        return (self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryMth") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryMthAWT") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_fixedSalaryMth") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_apprentice") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_internshipContract") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryHrs") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_fixedSalaryHrs") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryNoTimeConstraint") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_fixedSalaryNoTimeConstraint") +
                self.env.ref("l10n_ch_hr_payroll.l10n_ch_contract_type_administrativeBoard")).ids

    def generate_work_entries(self, date_start, date_stop, force=False):
        # Completely bypass work entry generation for Swiss Contracts
        swissdec_structure = self.env.ref("l10n_ch_hr_payroll.structure_type_employee_ch", raise_if_not_found=False)
        swiss_contracts = self.filtered(lambda c: c.structure_type_id.id == swissdec_structure.id)

        return super(HrContract, self - swiss_contracts).generate_work_entries(date_start, date_stop, force)

    def write(self, vals):
        res = super().write(vals)
        swissdec_structure = self.env.ref("l10n_ch_hr_payroll.structure_type_employee_ch", raise_if_not_found=False)
        swiss_employees = self.filtered(lambda c: c.structure_type_id.id == swissdec_structure.id).mapped("employee_id")
        if swiss_employees:
            pending_computation_slips = swiss_employees.sudo().slip_ids.filtered(lambda p: p.state in ['draft', 'verify'] and p.struct_id.code == "CHMONTHLYELM")
            if pending_computation_slips:
                earliest_payslip_date = min(pending_computation_slips.mapped('date_from'))
                swiss_employees.with_context(l10n_ch_reference_date=earliest_payslip_date)._create_or_update_snapshot()
                pending_computation_slips.action_refresh_from_work_entries()
            else:
                swiss_employees._create_or_update_snapshot()
        return res

    @api.depends("date_end")
    def _compute_l10n_ch_lpp_withdrawal_valid_as_of(self):
        for contract in self:
            if contract.date_end:
                contract.l10n_ch_lpp_withdrawal_valid_as_of = contract.date_end
            else:
                contract.l10n_ch_lpp_withdrawal_valid_as_of = False

    @api.depends("date_start")
    def _compute_l10n_ch_lpp_entry_valid_as_of(self):
        for contract in self:
            if contract.date_end:
                contract.l10n_ch_lpp_entry_valid_as_of = contract.date_start
            else:
                contract.l10n_ch_lpp_entry_valid_as_of = False

    @api.depends('employee_id.l10n_ch_other_employment')
    def _compute_l10n_ch_other_employers(self):
        for contract in self:
            if contract.employee_id.l10n_ch_other_employment:
                contract.l10n_ch_other_employers = True
            else:
                contract.l10n_ch_other_employers = False

    @api.depends('employee_id.l10n_ch_other_employment', 'employee_id.l10n_ch_total_activity_type', 'employee_id.l10n_ch_other_activity_percentage')
    def _compute_l10n_ch_other_employers_occupation_rate(self):
        for contract in self:
            if contract.employee_id.l10n_ch_other_employment and contract.employee_id.l10n_ch_total_activity_type == 'percentage':
                contract.l10n_ch_other_employers_occupation_rate = contract.employee_id.l10n_ch_other_activity_percentage
            else:
                contract.l10n_ch_other_employers_occupation_rate = 0

    @api.depends('l10n_ch_location_unit_id')
    def _compute_l10n_ch_weekly_hours(self):
        for contract in self:
            if contract.l10n_ch_location_unit_id:
                contract.l10n_ch_weekly_hours = contract.l10n_ch_location_unit_id.weekly_hours

    @api.depends('l10n_ch_location_unit_id', 'l10n_ch_weekly_hours')
    def _compute_l10n_ch_current_occupation_rate(self):
        for contract in self:
            rate = 0
            if contract.l10n_ch_location_unit_id.weekly_hours > 0:
                rate += (contract.l10n_ch_weekly_hours / contract.l10n_ch_location_unit_id.weekly_hours) * 100
            if contract.l10n_ch_location_unit_id.weekly_lessons > 0:
                rate += (contract.l10n_ch_weekly_lessons / contract.l10n_ch_location_unit_id.weekly_lessons) * 100

            contract.l10n_ch_current_occupation_rate = rate

    def _inverse_l10n_ch_current_occupation_rate(self):
        for contract in self:
            if contract.l10n_ch_location_unit_id.weekly_hours > 0:
                contract.l10n_ch_weekly_hours = (contract.l10n_ch_location_unit_id.weekly_hours * contract.l10n_ch_current_occupation_rate) / 100

    @api.depends("l10n_ch_yearly_holidays")
    def _compute_l10n_ch_contractual_holidays_rate(self):
        for contract in self:
            contract.l10n_ch_contractual_holidays_rate = round((contract.l10n_ch_yearly_holidays / (260 - contract.l10n_ch_yearly_holidays)) * 100, 2)

    @api.depends("l10n_ch_yearly_paid_public_holidays")
    def _compute_l10n_ch_contractual_public_holidays_rate(self):
        for contract in self:
            contract.l10n_ch_contractual_public_holidays_rate = round((contract.l10n_ch_yearly_paid_public_holidays / (260 - contract.l10n_ch_yearly_paid_public_holidays)) * 100, 2)

    @api.depends('structure_type_id', 'contract_type_id')
    def _compute_wage_type(self):
        swissdec_structure = self.env.ref("l10n_ch_hr_payroll.hr_payroll_structure_ch_employee_salary")
        swissdec_contracts = self.filtered(lambda c: c.structure_type_id.id == swissdec_structure.id)
        for contract in swissdec_contracts:
            if contract.contract_type_id.code in ["indefiniteSalaryMth", "indefiniteSalaryMthAWT", "fixedSalaryMth", "apprentice", "internshipContract"]:
                contract.wage_type = "monthly"
            elif contract.contract_type_id.code in ["indefiniteSalaryHrs", "fixedSalaryHrs"]:
                contract.wage_type = "hourly"
            else:
                contract.wage_type = "NoTimeConstraint"

        super(HrContract, self - swissdec_contracts)._compute_wage_type()

    def action_view_wages(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('l10n_ch_hr_payroll_elm_transmission.action_l10n_ch_hr_contract_wage')
        action['domain'] = [('contract_id', '=', self.id),
                            ('date_start', '!=', False)]
        action['context'] = {
            'default_contract_id': self.id
        }

        return action

    def _compute_one_time_wage_count(self):
        grouped_wages = dict(self.env['l10n.ch.hr.contract.wage']._read_group(domain=[('contract_id', 'in', self.ids),
                                                                 ('date_start', '!=', False)],
                                                         groupby=['contract_id'], aggregates=['contract_id:count']))

        for contract in self:
            contract.one_time_wage_count = grouped_wages.get(contract, 0)
