# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


# YTI TODO: Split me into 2 files
class HrContract(models.Model):
    _inherit = 'hr.contract'

    transport_mode_car = fields.Boolean('Uses company car')
    transport_mode_public = fields.Boolean('Uses public transportation')
    transport_mode_others = fields.Boolean('Uses another transport mode')
    car_atn = fields.Monetary(string='ATN Company Car')
    public_transport_employee_amount = fields.Monetary('Paid by the employee (Monthly)')
    warrant_value_employee = fields.Monetary(compute='_compute_warrants_cost', string="Warrant value for the employee")

    # Employer costs fields
    final_yearly_costs = fields.Monetary(compute='_compute_final_yearly_costs',
        readonly=False, store=True,
        string="Employee Budget",
        tracking=True,
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
        tracking=True,
        help="Monthly gross amount that the employee receives if the target is reached.")
    fuel_card = fields.Monetary(string="Fuel Card",
        tracking=True,
        help="Monthly amount the employee receives on his fuel card.")
    internet = fields.Monetary(string="Internet",
        tracking=True,
        help="The employee's internet subcription will be paid up to this amount.")
    representation_fees = fields.Monetary(string="Representation Fees",
        tracking=True,
        help="Monthly net amount the employee receives to cover his representation fees.")
    mobile = fields.Monetary(string="Mobile",
        tracking=True,
        help="The employee's mobile subscription will be paid up to this amount.")
    mobile_plus = fields.Monetary(string="International Communication",
        tracking=True,
        help="The employee's mobile subscription for international communication will be paid up to this amount.")
    meal_voucher_amount = fields.Monetary(string="Meal Vouchers",
        tracking=True,
        help="Amount the employee receives in the form of meal vouchers per worked day.")
    holidays = fields.Float(string='Paid Time Off',
        help="Number of days of paid leaves the employee gets per year.")
    wage_with_holidays = fields.Monetary(compute='_compute_wage_with_holidays', inverse='_inverse_wage_with_holidays',
        tracking=True, string="Wage update with holidays retenues")
    eco_checks = fields.Monetary("Eco Vouchers",
        help="Yearly amount the employee receives in the form of eco vouchers.")
    ip = fields.Boolean(default=False, tracking=True)
    ip_wage_rate = fields.Float(string="IP percentage", help="Should be between 0 and 100 %")

    @api.constrains('ip_wage_rate')
    def _check_ip_wage_rate(self):
        if self.filtered(lambda contract: contract.ip_wage_rate < 0 or contract.ip_wage_rate > 100):
            raise ValidationError(_('The IP rate on wage should be between 0 and 100'))

    @api.depends('holidays', 'wage', 'final_yearly_costs')
    def _compute_wage_with_holidays(self):
        for contract in self:
            if contract.holidays:
                yearly_cost = contract.final_yearly_costs * (1.0 - contract.holidays / 231.0)
                contract.wage_with_holidays = contract._get_gross_from_employer_costs(yearly_cost)
            else:
                contract.wage_with_holidays = contract.wage

    def _inverse_wage_with_holidays(self):
        for contract in self:
            if contract.holidays:
                remaining_for_gross = contract.wage_with_holidays * (13.0 + 13.0 * 0.3507 + 0.92)
                yearly_cost = remaining_for_gross \
                    + 12.0 * contract.representation_fees \
                    + 12.0 * contract.fuel_card \
                    + 12.0 * contract.internet \
                    + 12.0 * (contract.mobile + contract.mobile_plus) \
                    + 12.0 * contract.transport_employer_cost \
                    + contract.warrants_cost \
                    + 220.0 * contract.meal_voucher_paid_by_employer
                contract.final_yearly_costs = yearly_cost / (1.0 - contract.holidays / 231.0)
                contract.wage = contract._get_gross_from_employer_costs(contract.final_yearly_costs)
            else:
                contract.wage = contract.wage_with_holidays

    @api.depends('transport_mode_car', 'transport_mode_public', 'transport_mode_others',
        'company_car_total_depreciated_cost', 'public_transport_reimbursed_amount', 'others_reimbursed_amount')
    def _compute_transport_employer_cost(self):
        # Don't call to super has we ovewrite the method
        for contract in self:
            transport_employer_cost = 0.0
            if contract.transport_mode_car:
                transport_employer_cost += contract.company_car_total_depreciated_cost
            if contract.transport_mode_public:
                transport_employer_cost += contract.public_transport_reimbursed_amount
            if contract.transport_mode_others:
                transport_employer_cost += contract.others_reimbursed_amount
            contract.transport_employer_cost = transport_employer_cost

    @api.depends('commission_on_target')
    def _compute_warrants_cost(self):
        for contract in self:
            contract.warrants_cost = contract.commission_on_target * 1.326 / 1.05 * 12.0
            contract.warrant_value_employee = contract.commission_on_target * 1.326 * (1.00 - 0.535) * 12.0

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
        'social_security_contributions', 'warrants_cost', 'meal_voucher_paid_by_employer')
    def _compute_final_yearly_costs(self):
        for contract in self:
            contract.final_yearly_costs = (
                contract.yearly_cost_before_charges +
                contract.social_security_contributions +
                contract.wage * 0.92 +
                contract.warrants_cost +
                (220.0 * contract.meal_voucher_paid_by_employer)
            )

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

    @api.onchange('transport_mode_car', 'transport_mode_public', 'transport_mode_others')
    def _onchange_transport_mode(self):
        if not self.transport_mode_car:
            self.fuel_card = 0
            self.company_car_total_depreciated_cost = 0
        if not self.transport_mode_others:
            self.others_reimbursed_amount = 0
        if not self.transport_mode_public:
            self.public_transport_reimbursed_amount = 0

    @api.onchange('mobile', 'mobile_plus')
    def _onchange_mobile(self):
        if self.mobile_plus and not self.mobile:
            raise ValidationError(_('You should have a mobile subscription to select an international communication amount.'))

    def _get_mobile_amount(self, has_mobile, international_communication):
        if has_mobile and international_communication:
            return self.env['ir.default'].sudo().get('hr.contract', 'mobile') + self.env['ir.default'].sudo().get('hr.contract', 'mobile_plus')
        if has_mobile:
            return self.env['ir.default'].sudo().get('hr.contract', 'mobile')
        return 0.0

    def _get_gross_from_employer_costs(self, yearly_cost):
        contract = self
        remaining_for_gross = yearly_cost \
            - 12.0 * contract.representation_fees \
            - 12.0 * contract.fuel_card \
            - 12.0 * contract.internet \
            - 12.0 * (contract.mobile + contract.mobile_plus) \
            - 12.0 * contract.transport_employer_cost \
            - contract.warrants_cost \
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
