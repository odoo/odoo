# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    transport_mode = fields.Selection([
        ('company_car', 'Company car'),
        ('public_transport', 'Public Transport'),
        ('others', 'Other'),
    ], string="Transport", default='company_car',
    help="Transport mode the employee uses to go to work.")
    car_atn = fields.Monetary(string='ATN Company Car')
    public_transport_employee_amount = fields.Monetary('Paid by the employee (Monthly)')
    thirteen_month = fields.Monetary(compute='_compute_holidays_advantages', string='13th Month',
        help="Yearly gross amount the employee receives as 13th month bonus.")
    double_holidays = fields.Monetary(compute='_compute_holidays_advantages', string='Holiday Bonus',
        help="Yearly gross amount the employee receives as holidays bonus.")
    warrant_value_employee = fields.Monetary(compute='_compute_warrants_cost', string="Warrant value for the employee")

    # Employer costs fields
    final_yearly_costs = fields.Monetary(compute='_compute_final_yearly_costs', readonly=False,
        string='Total Employee Cost', groups="hr.group_hr_manager",
        help="Total yearly cost of the employee for the employer.")
    monthly_yearly_costs = fields.Monetary(compute='_compute_monthly_yearly_costs', string='Monthly Equivalent Cost', readonly=True,
        help="Total monthly cost of the employee for the employer.")
    ucm_insurance = fields.Monetary(compute='_compute_ucm_insurance', string="Social Secretary Costs")
    social_security_contributions = fields.Monetary(compute='_compute_social_security_contributions', string="Social Security Contributions")
    yearly_cost_before_charges = fields.Monetary(compute='_compute_yearly_cost_before_charges', string="Yearly Costs Before Charges")
    meal_voucher_paid_by_employer = fields.Monetary(compute='_compute_meal_voucher_paid_by_employer', string="Meal Voucher Paid by Employer")
    company_car_total_depreciated_cost = fields.Monetary()
    public_transport_reimbursed_amount = fields.Monetary(string='Reimbursed amount',
        compute='_compute_public_transport_reimbursed_amount', readonly=False, store=True)
    others_reimbursed_amount = fields.Monetary(string='Other Reimbursed amount')
    transport_employer_cost = fields.Monetary(compute='_compute_transport_employer_cost', string="Employer cost from employee transports")
    warrants_cost = fields.Monetary(compute='_compute_warrants_cost')

    # Advantages
    commission_on_target = fields.Monetary(string="Commission on Target",
        default=lambda self: self.get_attribute('commission_on_target', 'default_value'),
        help="Monthly gross amount that the employee receives if the target is reached.")
    fuel_card = fields.Monetary(string="Fuel Card",
        default=lambda self: self.get_attribute('fuel_card', 'default_value'),
        help="Monthly amount the employee receives on his fuel card.")
    internet = fields.Monetary(string="Internet",
        default=lambda self: self.get_attribute('internet', 'default_value'),
        help="The employee's internet subcription will be paid up to this amount.")
    representation_fees = fields.Monetary(string="Representation Fees",
        default=lambda self: self.get_attribute('representation_fees', 'default_value'),
        help="Monthly net amount the employee receives to cover his representation fees.")
    mobile = fields.Monetary(string="Mobile",
        default=lambda self: self.get_attribute('mobile', 'default_value'),
        help="The employee's mobile subscription will be paid up to this amount.")
    mobile_plus = fields.Monetary(string="International Communication",
        default=lambda self: self.get_attribute('mobile_plus', 'default_value'),
        help="The employee's mobile subscription for international communication will be paid up to this amount.")
    meal_voucher_amount = fields.Monetary(string="Meal Vouchers",
        default=lambda self: self.get_attribute('meal_voucher_amount', 'default_value'),
        help="Amount the employee receives in the form of meal vouchers per worked day.")
    holidays = fields.Float(string='Legal Leaves',
        default=lambda self: self.get_attribute('holidays', 'default_value'),
        help="Number of days of paid leaves the employee gets per year.")
    holidays_editable = fields.Boolean(string="Editable Leaves", default=True)
    holidays_compensation = fields.Monetary(compute='_compute_holidays_compensation', string="Holidays Compensation")
    wage_with_holidays = fields.Monetary(compute='_compute_wage_with_holidays', inverse='_inverse_wage_with_holidays', string="Wage update with holidays retenues")
    additional_net_amount = fields.Monetary(string="Net Supplements",
        help="Monthly net amount the employee receives.")
    retained_net_amount = fields.Monetary(sting="Net Retained",
        help="Monthly net amount that is retained on the employee's salary.")
    eco_checks = fields.Monetary("Eco Vouchers",
        default=lambda self: self.get_attribute('eco_checks', 'default_value'),
        help="Yearly amount the employee receives in the form of eco vouchers.")

    @api.depends('holidays', 'wage', 'final_yearly_costs')
    def _compute_wage_with_holidays(self):
        for contract in self:
            if contract.holidays > 20.0:
                yearly_cost = contract.final_yearly_costs * (1.0 - (contract.holidays - 20.0) / 231.0)
                contract.wage_with_holidays = contract._get_gross_from_employer_costs(yearly_cost)
            else:
                contract.wage_with_holidays = contract.wage

    def _inverse_wage_with_holidays(self):
        for contract in self:
            if contract.holidays > 20.0:
                remaining_for_gross = contract.wage_with_holidays * (13.0 + 13.0 * 0.3507 + 0.92)
                yearly_cost = remaining_for_gross \
                    + 12.0 * contract.representation_fees \
                    + 12.0 * contract.fuel_card \
                    + 12.0 * contract.internet \
                    + 12.0 * (contract.mobile + contract.mobile_plus) \
                    + 12.0 * contract.transport_employer_cost \
                    + (1.326 / 1.05 * 12.0) * contract.commission_on_target \
                    + 220.0 * contract.meal_voucher_paid_by_employer
                contract.final_yearly_costs = yearly_cost / (1.0 - (contract.holidays - 20.0) / 231.0)
                contract.wage = contract._get_gross_from_employer_costs(contract.final_yearly_costs)
            else:
                contract.wage = contract.wage_with_holidays

    @api.depends('transport_mode', 'company_car_total_depreciated_cost',
        'public_transport_reimbursed_amount', 'others_reimbursed_amount')
    def _compute_transport_employer_cost(self):
        for contract in self:
            if contract.transport_mode == 'company_car':
                contract.transport_employer_cost = contract.company_car_total_depreciated_cost
            elif contract.transport_mode == 'public_transport':
                contract.transport_employer_cost = contract.public_transport_reimbursed_amount
            elif contract.transport_mode == 'others':
                contract.transport_employer_cost = contract.others_reimbursed_amount

    @api.depends('commission_on_target')
    def _compute_warrants_cost(self):
        for contract in self:
            contract.warrants_cost = contract.commission_on_target * 1.326 / 1.05 * 12.0
            contract.warrant_value_employee = contract.warrants_cost * 0.54

    @api.depends('wage', 'fuel_card', 'representation_fees', 'transport_employer_cost',
        'internet', 'mobile', 'mobile_plus')
    def _compute_yearly_cost_before_charges(self):
        for contract in self:
            contract.yearly_cost_before_charges = 12.0 * (
                contract.wage * (1.0 + 1.0 / 12.0) +
                contract.fuel_card +
                contract.representation_fees +
                contract.internet +
                contract.mobile +
                contract.mobile_plus +
                contract.transport_employer_cost
            )

    @api.depends('yearly_cost_before_charges', 'social_security_contributions', 'wage',
        'social_security_contributions', 'double_holidays', 'warrants_cost', 'meal_voucher_paid_by_employer')
    def _compute_final_yearly_costs(self):
        for contract in self:
            contract.final_yearly_costs = (
                contract.yearly_cost_before_charges +
                contract.social_security_contributions +
                contract.double_holidays +
                contract.warrants_cost +
                (220.0 * contract.meal_voucher_paid_by_employer)
            )

    @api.depends('holidays', 'final_yearly_costs')
    def _compute_holidays_compensation(self):
        for contract in self:
            if contract.holidays < 20:
                decrease_amount = contract.final_yearly_costs * (20.0 - contract.holidays) / 231.0
                contract.holidays_compensation = decrease_amount
            else:
                contract.holidays_compensation = 0.0

    @api.onchange('final_yearly_costs')
    def _onchange_final_yearly_costs(self):
        self.wage = self._get_gross_from_employer_costs(self.final_yearly_costs)

    @api.depends('meal_voucher_amount')
    def _compute_meal_voucher_paid_by_employer(self):
        for contract in self:
            contract.meal_voucher_paid_by_employer = contract.meal_voucher_amount * (1 - 0.1463)

    @api.depends('wage')
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

    @api.onchange('transport_mode')
    def _onchange_transport_mode(self):
        if self.transport_mode != 'company_car':
            self.fuel_card = 0
            self.company_car_total_depreciated_cost = 0
        if self.transport_mode != 'others':
            self.others_reimbursed_amount = 0
        if self.transport_mode != 'public_transports':
            self.public_transport_reimbursed_amount = 0

    @api.onchange('mobile', 'mobile_plus')
    def _onchange_mobile(self):
        if self.mobile_plus and not self.mobile:
            raise ValidationError(_('You should have a mobile subscription to select an international communication amount!'))

    def _get_internet_amount(self, has_internet):
        if has_internet:
            return self.get_attribute('internet', 'default_value')
        else:
            return 0.0

    def _get_mobile_amount(self, has_mobile, international_communication):
        if has_mobile and international_communication:
            return self.get_attribute('mobile', 'default_value') + self.get_attribute('mobile_plus', 'default_value')
        elif has_mobile:
            return self.get_attribute('mobile', 'default_value')
        else:
            return 0.0

    def _get_gross_from_employer_costs(self, yearly_cost):
        contract = self
        remaining_for_gross = yearly_cost \
            - 12.0 * contract.representation_fees \
            - 12.0 * contract.fuel_card \
            - 12.0 * contract.internet \
            - 12.0 * (contract.mobile + contract.mobile_plus) \
            - 12.0 * contract.transport_employer_cost \
            - (1.326 / 1.05 * 12.0) * contract.commission_on_target \
            - 220.0 * contract.meal_voucher_paid_by_employer
        gross = remaining_for_gross / (13.0 + 13.0 * 0.3507 + 0.92)
        return gross


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    spouse_fiscal_status = fields.Selection([
        ('without income', 'Without Income'),
        ('with income', 'With Income')
    ], string='Tax status for spouse', groups="hr.group_hr_user")
    disabled = fields.Boolean(string="Disabled", help="If the employee is declared disabled by law", groups="hr.group_hr_user")
    disabled_spouse_bool = fields.Boolean(string='Disabled Spouse', help='if recipient spouse is declared disabled by law', groups="hr.group_hr_user")
    disabled_children_bool = fields.Boolean(string='Disabled Children', help='if recipient children is/are declared disabled by law', groups="hr.group_hr_user")
    resident_bool = fields.Boolean(string='Nonresident', help='if recipient lives in a foreign country', groups="hr.group_hr_user")
    disabled_children_number = fields.Integer('Number of disabled children', groups="hr.group_hr_user")
    dependent_children = fields.Integer(compute='_compute_dependent_children', string='Considered number of dependent children', groups="hr.group_hr_user")
    other_dependent_people = fields.Boolean(string="Other Dependent People", help="If other people are dependent on the employee", groups="hr.group_hr_user")
    other_senior_dependent = fields.Integer('# seniors (>=65)', help="Number of seniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user")
    other_disabled_senior_dependent = fields.Integer('# disabled seniors (>=65)', groups="hr.group_hr_user")
    other_juniors_dependent = fields.Integer('# people (<65)', help="Number of juniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user")
    other_disabled_juniors_dependent = fields.Integer('# disabled people (<65)', groups="hr.group_hr_user")
    dependent_seniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent seniors", groups="hr.group_hr_user")
    dependent_juniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent juniors", groups="hr.group_hr_user")
    spouse_net_revenue = fields.Float(string="Spouse Net Revenue", help="Own professional income, other than pensions, annuities or similar income", groups="hr.group_hr_user")
    spouse_other_net_revenue = fields.Float(string="Spouse Other Net Revenue",
        help='Own professional income which is exclusively composed of pensions, annuities or similar income', groups="hr.group_hr_user")

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

    @api.depends('other_dependent_people', 'other_senior_dependent',
        'other_disabled_senior_dependent', 'other_juniors_dependent', 'other_disabled_juniors_dependent')
    def _compute_dependent_people(self):
        for employee in self:
            employee.dependent_seniors = employee.other_senior_dependent + employee.other_disabled_senior_dependent
            employee.dependent_juniors = employee.other_juniors_dependent + employee.other_disabled_juniors_dependent
