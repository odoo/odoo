# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # See if can be done in hr.contract
    employee_id = fields.Many2one(required=False)

    transport_mode = fields.Selection([
        ('company_car', 'Company car'),
        ('public_transport', 'Public Transport'),
        ('others', 'Others'),
    ], string="Transport", default='company_car')
    car_atn = fields.Float(string='ATN Company Car')
    public_transport_employee_amount = fields.Float('Paid by the employee (Monthly)')
    public_transport_reimbursed_amount = fields.Float(compute='_compute_public_transport_reimbursed_amount', string='Reimbursed amount')
    others_employee_amount = fields.Float('Reimbursed by the employer (Monthly)')
    eco_checks = fields.Float('Eco-checks', default=250)
    thirteen_month = fields.Float(compute='_compute_holidays_advantages', string='13th Month')
    double_holidays = fields.Float(compute='_compute_holidays_advantages', string='Double holidays')
    group_insurance = fields.Float('Group Insurance')
    warrant_value_employee = fields.Float(compute='_compute_warrants_cost', string="Warrant value for the employee")

    # Employer costs fields
    final_yearly_costs = fields.Float(compute='_compute_final_yearly_costs', string='Final Yearly Costs', groups="hr.group_hr_manager")
    monthly_yearly_costs = fields.Float(compute='_compute_monthly_yearly_costs', string='Monthly Yearly Costs', readonly=True)
    ucm_insurance = fields.Float(compute='_compute_ucm_insurance', string="Social Secretary Costs")
    social_security_contributions = fields.Float(compute='_compute_social_security_contributions', string="Social Security Contributions")
    yearly_cost_before_charges = fields.Float(compute='_compute_yearly_cost_before_charges', string="Yearly Costs Before Charges")
    meal_voucher_paid_by_employer = fields.Float(compute='_compute_meal_voucher_paid_by_employer', string="Meal Voucher Paid by Employer")
    company_car_total_depreciated_cost = fields.Float()
    warrants_cost = fields.Float(compute='_compute_warrants_cost')

    @api.depends('advantage_ids', 'advantage_ids.value')
    def _compute_warrants_cost(self):
        for contract in self:
            contract.warrants_cost = contract.get_value('commission_on_target') * 1.326 / 1.05 * 12.0
            contract.warrant_value_employee = contract.warrants_cost * 0.54

    @api.depends('wage', 'advantage_ids', 'company_car_total_depreciated_cost')
    def _compute_yearly_cost_before_charges(self):
        for contract in self:
            # import pdb; pdb.set_trace()
            contract.yearly_cost_before_charges = 12.0 * (
                contract.wage * (1.0 + 1.0 / 12.0) +
                contract.get_value('fuel_card') +
                contract.get_value('representation_fees') +
                contract.get_value('internet') +
                contract.get_value('mobile') +
                contract.get_value('mobile_plus') +
                contract.company_car_total_depreciated_cost
            )

    @api.depends('yearly_cost_before_charges')
    def _compute_final_yearly_costs(self):
        for contract in self:
            contract.final_yearly_costs = (
                contract.yearly_cost_before_charges +
                contract.ucm_insurance +
                contract.social_security_contributions +
                contract.double_holidays +
                contract.warrants_cost +
                (220.0 * contract.meal_voucher_paid_by_employer)
            )

    @api.depends('advantage_ids', 'advantage_ids.value')
    def _compute_meal_voucher_paid_by_employer(self):
        for contract in self:
            contract.meal_voucher_paid_by_employer = contract.get_value('meal_voucher_amount') * (1 - 0.1463)

    @api.depends('wage', 'advantage_ids.value')
    def _compute_social_security_contributions(self):
        for contract in self:
            total_wage = contract.wage * 13.0
            contract.social_security_contributions = (total_wage) * 0.3507

    @api.depends('wage')
    def _compute_ucm_insurance(self):
        for contract in self:
            contract.ucm_insurance = (contract.wage * 12.0) * 0.05

    @api.depends('public_transport_employee_amount')
    def _compute_public_transport_reimbursed_amount(self):
        for contract in self:
            contract.public_transport_reimbursed_amount = contract._get_public_transport_reimbursed_amount(contract.public_transport_employee_amount)

    def _get_public_transport_reimbursed_amount(self, amount):
        return amount * 0.68

    @api.depends('final_yearly_costs')
    def _compute_monthly_yearly_costs(self):
        for contract in self:
            contract.monthly_yearly_costs = contract.final_yearly_costs / 12.0

    @api.depends('wage')
    def _compute_holidays_advantages(self):
        for contract in self:
            contract.double_holidays = contract.wage * 0.92
            contract.thirteen_month = contract.wage

    def _get_internet_amount(self, has_internet):
        default_value = self.get_attribute('internet', 'default_value')
        if has_internet:
            return default_value
        else:
            return 0.0

    def _get_mobile_amount(self, has_mobile, international_communication):
        values = self.get_attribute('mobile', 'advantage_values')
        if has_mobile and international_communication:
            return values[1].value
        elif has_mobile:
            return values[0].value
        else:
            return 0.0

    def _get_gross_from_employer_costs(self, yearly_cost):
        contract = self
        remaining_for_gross = yearly_cost \
            - 12.0 * contract.get_value('representation_fees') \
            - 12.0 * contract.get_value('fuel_card') \
            - 12.0 * contract.get_value('internet') \
            - 12.0 * (contract.get_value('mobile') + contract.get_value('mobile_plus')) \
            - 12.0 * contract.company_car_total_depreciated_cost \
            - (1.326 / 1.05 * 12.0) * contract.get_value('commission_on_target') \
            - 220.0 * contract.meal_voucher_paid_by_employer
        gross = remaining_for_gross / (12.0 * 0.05 + 13.0 + 13.0 * 0.3507 + 0.92)
        return gross

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    spouse_fiscal_status = fields.Selection([
        ('without income', 'Without Income'),
        ('with income', 'With Income')
    ], string='Tax status for spouse')
    disabled = fields.Boolean(string="Disabled", help="If the employee is declared disabled by law")
    disabled_spouse_bool = fields.Boolean(string='Disabled Spouse', help='if recipient spouse is declared disabled by law')
    disabled_children_bool = fields.Boolean(string='Disabled Children', help='if recipient children is/are declared disabled by law')
    resident_bool = fields.Boolean(string='Nonresident', help='if recipient lives in a foreign country')
    disabled_children_number = fields.Integer('Number of disabled children')
    dependent_children = fields.Integer(compute='_compute_dependent_children', string='Considered number of dependent children')
    other_dependent_people = fields.Boolean(string="Other Dependent People", help="If other people are dependent on the employee")
    other_senior_dependent = fields.Integer('# seniors (>=65)', help="Number of seniors dependent on the employee, including the disabled ones")
    other_disabled_senior_dependent = fields.Integer('# disabled seniors (>=65)')
    other_juniors_dependent = fields.Integer('# people (<65)', help="Number of juniors dependent on the employee, including the disabled ones")
    other_disabled_juniors_dependent = fields.Integer('# disabled people (<65)')
    dependent_seniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent seniors")
    dependent_juniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent juniors")
    spouse_net_revenue = fields.Float(string="Spouse Net Revenue", help="Own professional income, other than pensions, annuities or similar income")
    spouse_other_net_revenue = fields.Float(string="Spouse Other Net Revenue", help='Own professional income which is exclusively composed of pensions, annuities or similar income')

    @api.constrains('spouse_fiscal_status', 'spouse_net_revenue', 'spouse_other_net_revenue')
    def _check_spouse_revenue(self):
        for employee in self:
            if employee.spouse_fiscal_status == 'with income' and not employee.spouse_net_revenue and not employee.spouse_other_net_revenue:
                raise ValidationError(_("The revenue for the spouse can't be equal to zero is the fiscal status is 'With Income'."))

    @api.onchange('spouse_fiscal_status')
    def _onchange_spouse_fiscal_status(self):
        self.spouse_net_revenue = 0.0
        self.spouse_other_net_revenue = 0.0

    @api.onchange('disabled_children_bool')
    def _onchange_disabled_children_bool(self):
        self.disabled_children_number = 0

    @api.onchange('other_dependent_people')
    def _onchange_other_dependent_people(self):
        self.other_senior_dependent = 0.0
        self.other_disabled_senior_dependent = 0.0
        self.other_juniors_dependent = 0.0
        self.other_disabled_juniors_dependent = 0.0

    @api.depends('disabled_children_bool', 'disabled_children_number', 'children')
    def _compute_dependent_children(self):
        for employee in self:
            if employee.disabled_children_bool:
                employee.dependent_children = employee.children + employee.disabled_children_number
            else:
                employee.dependent_children = employee.children

    @api.depends('other_dependent_people', 'other_senior_dependent', 'other_disabled_senior_dependent', 'other_juniors_dependent', 'other_disabled_juniors_dependent')
    def _compute_dependent_people(self):
        for employee in self:
            employee.dependent_seniors = employee.other_senior_dependent + employee.other_disabled_senior_dependent
            employee.dependent_juniors = employee.other_juniors_dependent + employee.other_disabled_juniors_dependent
