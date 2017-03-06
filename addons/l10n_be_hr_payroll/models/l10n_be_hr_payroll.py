# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # See if can be done in hr.contract
    employee_id = fields.Many2one(required=False)

    has_internet = fields.Boolean('Internet', help="Enable this option if the employee has its internet reimbursed by the company")
    has_mobile = fields.Boolean('Mobile', help="Enable this option if the employee has its mobile contract reimbursed by the company")
    has_commission_on_target = fields.Boolean('Commissions on Target')
    international_communication = fields.Boolean('International Communication')
    transport_mode = fields.Selection([
        ('company_car', 'Company car'),
        ('public_transport', 'Public Transport'),
        ('others', 'Others'),
    ], string="Transport", default='company_car')
    car_id = fields.Many2one('fleet.vehicle', string='Car',
        domain=lambda self: self._get_available_cars_domain(),
        default=lambda self: self.env['fleet.vehicle'].search([('driver_id', '=', self.employee_id.address_home_id.id)], limit=1))
    car_atn = fields.Float(compute='_compute_car_atn_and_costs', string='ATN Company Car')
    available_cars_amount = fields.Integer(compute='_compute_available_cars_amount', string='Number of available cars')
    new_car = fields.Boolean('Request a new car')
    new_car_model_id = fields.Many2one('fleet.vehicle.model', string="Model", domain=lambda self: self._get_possible_model_domain())
    public_transport_employee_amount = fields.Float('Paid by the employee (Monthly)')
    public_transport_reimbursed_amount = fields.Float(compute='_compute_public_transport_reimbursed_amount', string='Reimbursed amount')
    others_employee_amount = fields.Float('Paid by the employee (Monthly)')
    eco_checks = fields.Float('Eco-checks', default=250)
    thirteen_month = fields.Float(compute='_compute_holidays_advantages', string='13th Month')
    double_holidays = fields.Float(compute='_compute_holidays_advantages', string='Double holidays')
    group_insurance = fields.Float('Group Insurance')

    # Employer costs fields
    final_yearly_costs = fields.Float(compute='_compute_final_yearly_costs', string='Final Yearly Costs', groups="hr.group_hr_manager")
    monthly_yearly_costs = fields.Float(compute='_compute_monthly_yearly_costs', string='Monthly Yearly Costs', readonly=True)
    ucm_insurance = fields.Float(compute='_compute_ucm_insurance', string="UCM + Insurance + etc")
    structural_reductions = fields.Float(compute='_compute_structural_reductions', string='Structural Reductions')
    social_security_contributions = fields.Float(compute='_compute_social_security_contributions', string="Social Security Contributions")
    yearly_cost_before_charges = fields.Float(compute='_compute_yearly_cost_before_charges', string="Yearly Costs Before Charges")
    meal_voucher_paid_by_employer = fields.Float(compute='_compute_meal_voucher_paid_by_employer', string="Meal Voucher Paid by Employer")
    company_car_total_depreciated_cost = fields.Float(compute='_compute_car_atn_and_costs')

    @api.depends('car_id', 'new_car', 'new_car_model_id')
    def _compute_car_atn_and_costs(self):
        for contract in self:
            if contract.car_id:
                contract.car_atn = contract.car_id.atn
                contract.company_car_total_depreciated_cost = contract.car_id.company_car_total_depreciated_cost
            elif contract.new_car and contract.new_car_model_id:
                contract.car_atn = contract.new_car_model_id.default_atn
                contract.company_car_total_depreciated_cost = contract.new_car_model_id.default_total_depreciated_cost

    @api.depends('name')
    def _compute_available_cars_amount(self):
        for contract in self:
            contract.available_cars_amount = self.env['fleet.vehicle'].search_count([('driver_id', '=', False)])

    @api.depends('wage', 'advantage_ids', 'company_car_total_depreciated_cost')
    def _compute_yearly_cost_before_charges(self):
        for contract in self:
            contract.yearly_cost_before_charges = 12.0 * (
                contract.wage * (1.0 + 1.0 / 12.0) +
                contract.get_value('fuel_card') +
                contract.get_value('representation_fees') +
                contract.get_value('internet') +
                contract.get_value('mobile') +
                contract.get_value('commission_on_target') +
                contract.company_car_total_depreciated_cost
            )

    @api.depends('yearly_cost_before_charges')
    def _compute_final_yearly_costs(self):
        for contract in self:
            contract.final_yearly_costs = (
                contract.yearly_cost_before_charges +
                contract.ucm_insurance +
                contract.structural_reductions +
                contract.social_security_contributions +
                contract.double_holidays +
                (220.0 * contract.meal_voucher_paid_by_employer)
            )

    @api.depends('advantage_ids', 'advantage_ids.value')
    def _compute_meal_voucher_paid_by_employer(self):
        for contract in self:
            contract.meal_voucher_paid_by_employer = contract.get_value('meal_voucher_amount') - contract.get_value('meal_voucher_employee_deduction')

    @api.depends('wage', 'has_commission_on_target')
    def _compute_social_security_contributions(self):
        for contract in self:
            total_wage = contract.wage * 13.0
            total_commissions = contract.get_value('commission_on_target') * 12.0
            contract.social_security_contributions = (total_wage + total_commissions) * 0.3507

    @api.depends('wage')
    def _compute_structural_reductions(self):
        # TODO: cde has to check the amount
        for contract in self:
            contract.structural_reductions = 0.0

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

    @api.onchange('has_internet')
    def _onchange_has_internet(self):
        self.set_value('internet', self._get_internet_amount(self.has_internet))

    def _get_internet_amount(self, has_internet):
        values = self.get_attribute('internet', 'advantage_values')
        if has_internet:
            return values[0].value
        else:
            return 0.0

    @api.onchange('has_mobile', 'international_communication')
    def _onchange_mobile(self):
        self.set_value('mobile', self._get_mobile_amount(self.has_mobile, self.international_communication))

    def _get_mobile_amount(self, has_mobile, international_communication):
        values = self.get_attribute('mobile', 'advantage_values')
        if has_mobile and international_communication:
            return values[1].value
        elif has_mobile:
            return values[0].value
        else:
            return 0.0

    @api.onchange('has_commission_on_target')
    def _onchange_has_commission_on_target(self):
        values = self.get_attribute('commission_on_target', 'advantage_values')
        if self.has_commission_on_target:
            self.set_value('commission_on_target', values[1].value)
        else:
            self.set_value('commission_on_target', values[0].value)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        super(HrContract, self)._onchange_employee_id()
        self.car_id = self.env['fleet.vehicle'].search([('driver_id', '=', self.employee_id.address_home_id.id)], limit=1)
        return {'domain': {'car_id': self._get_available_cars_domain()}}

    def _get_available_cars_domain(self):
        return ['|', ('driver_id', '=', False), ('driver_id', '=', self.employee_id.address_home_id.id)]

    def _get_possible_model_domain(self):
        return [('can_be_requested', '=', True)]

    def _get_gross_from_employer_costs(self, yearly_cost):
        contract = self
        remaining_for_gross = yearly_cost \
            - 12.0 * contract.get_value('representation_fees') \
            - 12.0 * contract.get_value('fuel_card') \
            - 12.0 * contract.get_value('internet') \
            - 12.0 * contract.get_value('mobile') \
            - 12.0 * contract.company_car_total_depreciated_cost \
            - contract.structural_reductions \
            - (12.0 * 0.3507 + 12.0) * contract.get_value('commission_on_target') \
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
        if self.disabled_children_bool:
            self.dependent_children = self.children + self.disabled_children_number
        else:
            self.dependent_children = self.children

    @api.depends('other_dependent_people', 'other_senior_dependent', 'other_disabled_senior_dependent', 'other_juniors_dependent', 'other_disabled_juniors_dependent')
    def _compute_dependent_people(self):
        self.dependent_seniors = self.other_senior_dependent + self.other_disabled_senior_dependent
        self.dependent_juniors = self.other_juniors_dependent + self.other_disabled_juniors_dependent
