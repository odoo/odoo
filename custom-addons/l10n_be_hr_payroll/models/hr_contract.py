# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY

from odoo import api, fields, models, _
from odoo.tools import float_round, date_utils
from odoo.tools.float_utils import float_compare
from odoo.exceptions import ValidationError

EMPLOYER_ONSS = 0.2714


class HrContract(models.Model):
    _inherit = 'hr.contract'

    transport_mode_car = fields.Boolean('Uses company car')
    transport_mode_private_car = fields.Boolean('Uses private car')
    transport_mode_train = fields.Boolean('Uses train transportation')
    transport_mode_public = fields.Boolean('Uses another public transportation')
    car_atn = fields.Monetary(string='Car BIK', help='Benefit in Kind (Company Car)')
    train_transport_employee_amount = fields.Monetary('Train transport paid by the employee (Monthly)')
    public_transport_employee_amount = fields.Monetary('Public transport paid by the employee (Monthly)')
    warrant_value_employee = fields.Monetary(compute='_compute_commission_cost', string="Warrant monthly value for the employee")

    meal_voucher_paid_by_employer = fields.Monetary(compute='_compute_meal_voucher_info', string="Meal Voucher Paid by Employer")
    meal_voucher_paid_monthly_by_employer = fields.Monetary(compute='_compute_meal_voucher_info')
    company_car_total_depreciated_cost = fields.Monetary()
    private_car_reimbursed_amount = fields.Monetary(compute='_compute_private_car_reimbursed_amount')
    km_home_work = fields.Integer(related="employee_id.km_home_work", related_sudo=True, readonly=False)
    train_transport_reimbursed_amount = fields.Monetary(
        string='Train Transport Reimbursed amount',
        compute='_compute_train_transport_reimbursed_amount', readonly=False, store=True)
    public_transport_reimbursed_amount = fields.Monetary(
        string='Public Transport Reimbursed amount',
        compute='_compute_public_transport_reimbursed_amount', readonly=False, store=True)
    warrants_cost = fields.Monetary(compute='_compute_commission_cost', string="Warrant monthly cost for the employer")
    yearly_commission = fields.Monetary(compute='_compute_commission_cost')
    yearly_commission_cost = fields.Monetary(compute='_compute_commission_cost')

    # Advantages
    commission_on_target = fields.Monetary(
        string="Commission",
        tracking=True,
        help="Monthly gross amount that the employee receives if the target is reached.")
    fuel_card = fields.Monetary(
        string="Fuel Card",
        tracking=True,
        help="Monthly amount the employee receives on his fuel card.")
    internet = fields.Monetary(
        string="Internet Subscription",
        tracking=True,
        help="The employee's internet subcription will be paid up to this amount.")
    representation_fees = fields.Monetary(
        string="Expense Fees",
        tracking=True,
        help="Monthly net amount the employee receives to cover his representation fees.")
    mobile = fields.Monetary(
        string="Mobile Subscription",
        tracking=True,
        help="The employee's mobile subscription will be paid up to this amount.")
    has_laptop = fields.Boolean(
        string="Laptop",
        tracking=True,
        help="A benefit in kind is paid when the employee uses its laptop at home.")
    has_bicycle = fields.Boolean(string="Bicycle to work", default=False, groups="hr_contract.group_hr_contract_manager",
        help="Use a bicycle as a transport mode to go to work")
    meal_voucher_amount = fields.Monetary(
        string="Meal Vouchers",
        tracking=True,
        help="Amount the employee receives in the form of meal vouchers per worked day.")
    meal_voucher_average_monthly_amount = fields.Monetary(compute="_compute_meal_voucher_info")
    eco_checks = fields.Monetary(
        "Eco Vouchers",
        help="Yearly amount the employee receives in the form of eco vouchers.")
    ip = fields.Boolean('Intellectual Property', default=False, tracking=True)
    ip_wage_rate = fields.Float(string="IP percentage", help="Should be between 0 and 100 %")
    ip_value = fields.Float(compute='_compute_ip_value')
    fiscal_voluntarism = fields.Boolean(
        string="Fiscal Voluntarism", default=False, tracking=True,
        help="Voluntarily increase withholding tax rate.")
    fiscal_voluntary_rate = fields.Float(string="Fiscal Voluntary Rate", help="Should be between 0 and 100 %")
    no_onss = fields.Boolean(string="No ONSS")
    no_withholding_taxes = fields.Boolean()
    rd_percentage = fields.Integer("Time Percentage in R&D")
    employee_age = fields.Integer('Age of Employee', compute='_compute_employee_age', compute_sudo=True)
    l10n_be_impulsion_plan = fields.Selection([
        ('25yo', '< 25 years old'),
        ('12mo', '12 months +'),
        ('55yo', '55+ years old')], string="Impulsion Plan")
    l10n_be_onss_restructuring = fields.Boolean(string="Allow ONSS Reduction for Restructuring")

    has_hospital_insurance = fields.Boolean(string="Has Hospital Insurance", groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    insured_relative_children = fields.Integer(string="# Insured Children < 19 y/o", groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    insured_relative_adults = fields.Integer(string="# Insured Children >= 19 y/o", groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    insured_relative_spouse = fields.Boolean(string="Insured Spouse", groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    hospital_insurance_amount_per_child = fields.Float(string="Amount per Child", groups="hr_contract.group_hr_contract_employee_manager",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_child', default=7.2)))
    hospital_insurance_amount_per_adult = fields.Float(string="Amount per Adult", groups="hr_contract.group_hr_contract_employee_manager",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_adult', default=20.5)))
    insurance_amount = fields.Float(compute='_compute_insurance_amount', string="Insurance Amount", groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    insured_relative_adults_total = fields.Integer(compute='_compute_insured_relative_adults_total', groups="hr_contract.group_hr_contract_employee_manager")
    l10n_be_hospital_insurance_notes = fields.Text(string="Hospital Insurance: Additional Info")

    wage_with_holidays = fields.Monetary(
        string="Wage With Sacrifices",
        help="Adapted salary, according to the sacrifices defined on the contract (Example: Extra-legal time off, a percentage of the salary invested in a group insurance, etc...)")
    # Group Insurance
    l10n_be_group_insurance_rate = fields.Float(
        string="Group Insurance Sacrifice Rate", tracking=True,
        help="Should be between 0 and 100 %")
    l10n_be_group_insurance_amount = fields.Monetary(
        compute='_compute_l10n_be_group_insurance_amount', store=True)
    l10n_be_group_insurance_cost = fields.Monetary(
        compute='_compute_l10n_be_group_insurance_amount', store=True)
    # Ambulatory Insurance
    l10n_be_has_ambulatory_insurance = fields.Boolean(
        string="Has Ambulatory Insurance",
        groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    l10n_be_ambulatory_insured_children = fields.Integer(
        string="Ambulatory: # Insured Children < 19 y/o",
        groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    l10n_be_ambulatory_insured_adults = fields.Integer(
        string="Ambulatory: # Insured Children >= 19 y/o",
        groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    l10n_be_ambulatory_insured_spouse = fields.Boolean(
        string="Ambulatory: Insured Spouse",
        groups="hr_contract.group_hr_contract_employee_manager", tracking=True)
    l10n_be_ambulatory_amount_per_child = fields.Float(
        string="Ambulatory: Amount per Child", groups="hr_contract.group_hr_contract_employee_manager",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_child', default=7.2)))
    l10n_be_ambulatory_amount_per_adult = fields.Float(
        string="Ambulatory: Amount per Adult", groups="hr_contract.group_hr_contract_employee_manager",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_adult', default=20.5)))
    l10n_be_ambulatory_insurance_amount = fields.Float(
        compute='_compute_ambulatory_insurance_amount', string="Ambulatory: Insurance Amount",
        groups="hr_contract.group_hr_contract_employee_manager", compute_sudo=True, tracking=True)
    l10n_be_ambulatory_insured_adults_total = fields.Integer(
        compute='_compute_ambulatory_insured_adults_total',
        groups="hr_contract.group_hr_contract_employee_manager")
    l10n_be_ambulatory_insurance_notes = fields.Text(string="Ambulatory Insurance: Additional Info")


    l10n_be_is_below_scale = fields.Boolean(
        string="Is below CP200 salary scale", compute='_compute_l10n_be_is_below_scale', search='_search_l10n_be_is_below_scale', compute_sudo=True)
    l10n_be_is_below_scale_warning = fields.Char(compute='_compute_l10n_be_is_below_scale', compute_sudo=True)
    l10n_be_canteen_cost = fields.Monetary(string="Canteen Cost")

    _sql_constraints = [
        ('check_percentage_ip_rate', 'CHECK(ip_wage_rate >= 0 AND ip_wage_rate <= 100)', 'The IP rate on wage should be between 0 and 100.'),
        ('check_percentage_fiscal_voluntary_rate', 'CHECK(fiscal_voluntary_rate >= 0 AND fiscal_voluntary_rate <= 100)', 'The Fiscal Voluntary rate on wage should be between 0 and 100.'),
        ('check_percentage_group_insurance_rate', 'CHECK(l10n_be_group_insurance_rate >= 0 AND l10n_be_group_insurance_rate <= 100)', 'The group insurance salary sacrifice rate on wage should be between 0 and 100.'),
    ]

    @api.depends(
        'wage', 'state', 'employee_id.l10n_be_scale_seniority', 'job_id.l10n_be_scale_category',
        'work_time_rate', 'time_credit', 'resource_calendar_id.work_time_rate')
    def _compute_l10n_be_is_below_scale(self):
        # Source: https://emploi.belgique.be/fr/themes/remuneration/salaires-minimums-par-sous-commission-paritaire/banque-de-donnees-salaires
        student_stucture_type = self.env.ref('hr_contract.structure_type_employee_cp200')
        open_contracts = self.filtered(
            lambda c: c.state in ['draft', 'open']
            and c.company_id.country_id.code == 'BE'
            and c.employee_id
            and c._get_contract_wage()
            and c.structure_type_id == student_stucture_type)
        (self - open_contracts).write({
            'l10n_be_is_below_scale_warning': False,
            'l10n_be_is_below_scale': False
        })
        category_mapping = {
            'A': 0,
            'B': 1,
            'C': 2,
            'D': 3,
        }
        for contract in open_contracts:
            company_seniority = relativedelta(fields.Date.today(), contract.first_contract_date).years
            if not company_seniority:
                scales = self.env['hr.rule.parameter']._get_parameter_from_code('cp200_salary_scale_first_year', raise_if_not_found=False)
            else:
                scales = self.env['hr.rule.parameter']._get_parameter_from_code('cp200_salary_scale', raise_if_not_found=False)
            if not scales:
                # No existing scale (eg: contracts before 2021)
                contract.l10n_be_is_below_scale = False
                contract.l10n_be_is_below_scale_warning = False
                continue
            anterior_seniority = contract.employee_id.l10n_be_scale_seniority
            seniority = anterior_seniority + company_seniority
            category_index = category_mapping.get(contract.job_id.l10n_be_scale_category, 2)
            seniority_scale = scales.get(seniority, scales[26])
            min_wage = seniority_scale[category_index]
            if contract.time_credit:
                min_wage = min_wage * contract.work_time_rate
            else:
                min_wage = min_wage * contract.resource_calendar_id.work_time_rate / 100
            if contract._get_contract_wage() < min_wage:
                contract.l10n_be_is_below_scale = True
                contract.l10n_be_is_below_scale_warning = _("The wage is under the minimum scale of %s€ for a seniority of %s years.", round(min_wage, 2), seniority)
            else:
                contract.l10n_be_is_below_scale = False
                contract.l10n_be_is_below_scale_warning = False

    @api.model
    def _search_l10n_be_is_below_scale(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))
        below_contracts = self.env['hr.contract'].search(
            [('state', 'in', ['draft', 'open'])]
        ).filtered(lambda c: c.company_id.country_id.code == 'BE' and c.l10n_be_is_below_scale)

        if operator == '!=':
            value = not value
        return [('id', 'in' if value else 'not in', below_contracts.ids)]


    @api.model
    def _benefit_white_list(self):
        return super()._benefit_white_list() + [
            'insurance_amount',
            'ip_value',
            'l10n_be_ambulatory_insurance_amount',
            'meal_voucher_paid_monthly_by_employer',
        ]

    @api.onchange('has_hospital_insurance')
    def _onchange_has_hospital_insurance(self):
        if not self.has_hospital_insurance:
            self.insured_relative_spouse = False
            self.insured_relative_adults = 0
            self.insured_relative_children = 0

    @api.onchange('l10n_be_has_ambulatory_insurance')
    def _onchange_l10n_be_has_ambulatory_insurance(self):
        if not self.l10n_be_has_ambulatory_insurance:
            self.l10n_be_ambulatory_insured_spouse = False
            self.l10n_be_ambulatory_insured_adults = 0
            self.l10n_be_ambulatory_insured_children = 0


    @api.depends('has_hospital_insurance', 'insured_relative_adults', 'insured_relative_spouse')
    def _compute_insured_relative_adults_total(self):
        for contract in self:
            contract.insured_relative_adults_total = (
                int(contract.has_hospital_insurance)
                + contract.insured_relative_adults
                + int(contract.insured_relative_spouse))

    @api.model
    def _get_insurance_amount(self, child_amount, child_count, adult_amount, adult_count):
        return child_amount * child_count + adult_amount * adult_count

    @api.depends(
        'insured_relative_children', 'insured_relative_adults_total',
        'hospital_insurance_amount_per_child', 'hospital_insurance_amount_per_adult')
    def _compute_insurance_amount(self):
        for contract in self:
            contract.insurance_amount = contract._get_insurance_amount(
                contract.hospital_insurance_amount_per_child,
                contract.insured_relative_children,
                contract.hospital_insurance_amount_per_adult,
                contract.insured_relative_adults_total)

    @api.constrains('rd_percentage')
    def _check_discount_percentage(self):
        if self.filtered(lambda c: c.rd_percentage < 0 or c.rd_percentage > 100):
            raise ValidationError(_('The time Percentage in R&D should be between 0-100'))
        for contract in self:
            if contract.rd_percentage and contract.employee_id.certificate not in ['civil_engineer', 'doctor', 'master', 'bachelor']:
                raise ValidationError(_('Only employees with a Bachelor/Master/Doctor/Civil Engineer degree can benefit from the withholding taxes exemption.'))

    @api.depends('ip', 'ip_wage_rate')
    def _compute_ip_value(self):
        for contract in self:
            contract.ip_value = contract.ip_wage_rate if contract.ip else 0

    @api.depends('commission_on_target')
    def _compute_commission_cost(self):
        for contract in self:
            contract.warrants_cost = contract.commission_on_target * 1.326 / 1.05
            warrant_commission = contract.warrants_cost * 3.0
            cash_commission = contract.commission_on_target * 9.0
            contract.yearly_commission_cost = warrant_commission + cash_commission * (1 + EMPLOYER_ONSS)
            contract.yearly_commission = warrant_commission + cash_commission
            contract.warrant_value_employee = contract.commission_on_target * 1.326 * (1.00 - 0.535)

    @api.depends('meal_voucher_amount')
    def _compute_meal_voucher_info(self):
        # The amount of the meal voucher is computed on the basis of the contribution
        # of the employer and the employee. Indeed, the first can contribute up to a
        # maximum of € 6.91 per check and per day provided, while the participation
        # of the second must amount to a minimum of € 1.09.
        for contract in self:
            contract.meal_voucher_paid_by_employer = max(0, contract.meal_voucher_amount - 1.09)
            monthly_nb_meal_voucher = 220.0 / 12
            contract.meal_voucher_paid_monthly_by_employer = contract.meal_voucher_paid_by_employer * monthly_nb_meal_voucher
            contract.meal_voucher_average_monthly_amount = contract.meal_voucher_amount * monthly_nb_meal_voucher

    @api.depends('train_transport_employee_amount')
    def _compute_train_transport_reimbursed_amount(self):
        for contract in self:
            contract.train_transport_reimbursed_amount = contract._get_train_transport_reimbursed_amount(contract.train_transport_employee_amount)

    def _get_train_transport_reimbursed_amount(self, amount):
        return min(amount * 0.8, 311)

    @api.depends('public_transport_employee_amount')
    def _compute_public_transport_reimbursed_amount(self):
        for contract in self:
            contract.public_transport_reimbursed_amount = contract._get_public_transport_reimbursed_amount(contract.public_transport_employee_amount)

    @api.depends('employee_id')
    def _compute_employee_age(self):
        for contract in self:
            if not contract.employee_id or not contract.employee_id.birthday:
                contract.employee_age = 0
            else:
                contract.employee_age = relativedelta(fields.Date.today(), contract.employee_id.birthday).years

    def _get_public_transport_reimbursed_amount(self, amount):
        # As of February 1st, 2020, reimbursement for non-train-based public transportation,
        # when based on a flat fee, is computed as 71.8% of the actual cost, capped at the
        # reimbursement for 7 km of train-based transportation (34.00 EUR)
        # Source: http://www.cnt-nar.be/CCT-COORD/cct-019-09.pdf (Art. 4)
        return min(amount * 0.718, 34)

    @api.depends('km_home_work', 'transport_mode_private_car')
    def _compute_private_car_reimbursed_amount(self):
        for contract in self:
            if contract.transport_mode_private_car:
                amount = self._get_private_car_reimbursed_amount(contract.km_home_work)
            else:
                amount = 0.0
            contract.private_car_reimbursed_amount = amount

    @api.onchange('transport_mode_car', 'transport_mode_train', 'transport_mode_public')
    def _onchange_transport_mode(self):
        if not self.transport_mode_car:
            self.fuel_card = 0
            self.company_car_total_depreciated_cost = 0
        if not self.transport_mode_train:
            self.train_transport_reimbursed_amount = 0
        if not self.transport_mode_public:
            self.public_transport_reimbursed_amount = 0
        if self.transport_mode_car:
            self.transport_mode_private_car = False

    @api.onchange('transport_mode_private_car')
    def _onchange_transport_mode_private_car(self):
        if self.transport_mode_private_car:
            self.transport_mode_car = False
            self.fuel_card = 0

    @api.depends('holidays', 'wage', 'final_yearly_costs', 'l10n_be_group_insurance_rate')
    def _compute_wage_with_holidays(self):
        super()._compute_wage_with_holidays()

    @api.depends('wage', 'l10n_be_group_insurance_rate')
    def _compute_l10n_be_group_insurance_amount(self):
        for contract in self:
            rate = contract.l10n_be_group_insurance_rate
            insurance_amount = contract.wage * rate / 100.0
            contract.l10n_be_group_insurance_amount = insurance_amount
            # Example
            # 5 % salary configurator
            # 4.4 % insurance cost
            # 8.86 % ONSS
            # =-----------------------
            # 13.26 % over the 5%
            contract.l10n_be_group_insurance_cost = insurance_amount * (1 + 13.26 / 100.0)

    def _is_salary_sacrifice(self):
        self.ensure_one()
        return super()._is_salary_sacrifice() or self.l10n_be_group_insurance_rate

    def _get_yearly_cost_sacrifice_fixed(self):
        return super()._get_yearly_cost_sacrifice_fixed() + self._get_salary_costs_factor() * self.wage * self.l10n_be_group_insurance_rate / 100

    @api.depends('schedule_pay')
    def _compute_final_yearly_costs(self):
        return super()._compute_final_yearly_costs()

    def _get_salary_costs_factor(self):
        self.ensure_one()
        res = super()._get_salary_costs_factor()
        if self.structure_type_id == self.env.ref('hr_contract.structure_type_employee_cp200'):
            res = 13.92 + 13.0 * EMPLOYER_ONSS
        if self.l10n_be_group_insurance_rate:
            return res * (1.0 - self.l10n_be_group_insurance_rate / 100)
        return res

    @api.depends(
        'l10n_be_has_ambulatory_insurance',
        'l10n_be_ambulatory_insured_adults',
        'l10n_be_ambulatory_insured_spouse')
    def _compute_ambulatory_insured_adults_total(self):
        for contract in self:
            contract.l10n_be_ambulatory_insured_adults_total = (
                int(contract.l10n_be_has_ambulatory_insurance)
                + contract.l10n_be_ambulatory_insured_adults
                + int(contract.l10n_be_ambulatory_insured_spouse))

    @api.model
    def _get_ambulatory_insurance_amount(self, child_amount, child_count, adult_amount, adult_count):
        return child_amount * child_count + adult_amount * adult_count

    @api.depends(
        'l10n_be_ambulatory_insured_children', 'l10n_be_ambulatory_insured_adults_total',
        'l10n_be_ambulatory_amount_per_child', 'l10n_be_ambulatory_amount_per_adult')
    def _compute_ambulatory_insurance_amount(self):
        for contract in self:
            contract.l10n_be_ambulatory_insurance_amount = contract._get_ambulatory_insurance_amount(
                contract.l10n_be_ambulatory_amount_per_child,
                contract.l10n_be_ambulatory_insured_children,
                contract.l10n_be_ambulatory_amount_per_adult,
                contract.l10n_be_ambulatory_insured_adults_total)

    @api.model
    def _get_private_car_reimbursed_amount(self, distance):
        # monthly train subscription amount => half is reimbursed
        # Generally this is not mandatory
        # See: https://emploi.belgique.be/fr/themes/remuneration/intervention-de-lemployeur-dans-les-frais-de-deplacement-domicile-lieu-de
        # But this is the case for the CP200
        # See: https://www.sfonds200.be/fonds-social/infos-sectorielles/frais-de-transport/prive-2020
        private_car_reimbursement_scale = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'private_car_reimbursement_scale', date=self.env.context.get('payslip_date'), raise_if_not_found=False)
        if not private_car_reimbursement_scale:
            return 0
        for distance_boundary, amount in private_car_reimbursement_scale:
            if distance <= distance_boundary:
                return amount / 2
        return private_car_reimbursement_scale[-1][1] / 2

    @api.model
    def update_state(self):
        # Called by a cron
        # It sets the contract in red before the expiration of a credit time contract
        date_today = fields.Date.today()
        outdated_days = date_today + relativedelta(days=14)
        nearly_expired_contracts = self.search([
            ('state', '=', 'open'),
            ('kanban_state', '!=', 'blocked'),
            ('time_credit', '=', True),
            ('date_end', '<', outdated_days),
        ])
        nearly_expired_contracts.write({'kanban_state': 'blocked'})
        return super().update_state()

    def _preprocess_work_hours_data_split_half(self, work_data, date_from, date_to):
        """
        Method is meant to be overriden, see l10n_be_hr_payroll_attendance
        """
        return

    def _get_work_hours_split_half(self, date_from, date_to, domain=None):
        """
        Returns the amount (expressed in hours) of work
        for a contract between two dates.
        If called on multiple contracts, sum work amounts of each contract.
        :param date_from: The start date
        :param date_to: The end date
        :returns: a dictionary {(half/full, work_entry_id_1): hours_1, (half/full, work_entry_id_2): hours_2}
        """
        date_from = datetime.combine(date_from, datetime.min.time())
        date_to = datetime.combine(date_to, datetime.max.time())
        work_data = defaultdict(lambda: list([0, 0]))  # [days, hours]
        number_of_hours_full_day = self.resource_calendar_id._get_max_number_of_hours(date_from, date_to)

        # First, found work entry that didn't exceed interval.
        work_entries = self.env['hr.work.entry']._read_group(
            self._get_work_hours_domain(date_from, date_to, domain=domain, inside=True),
            ['date_start:day', 'work_entry_type_id'],
            ['duration:sum']
        )

        self._preprocess_work_hours_data_split_half(work_entries, date_from, date_to)

        for _date_start_day, work_entry_type, duration_sum in work_entries:
            work_entry_type_id = work_entry_type.id
            if float_compare(duration_sum, number_of_hours_full_day, 2) != -1:
                if number_of_hours_full_day:
                    number_of_days = float_round(duration_sum / number_of_hours_full_day, precision_rounding=1, rounding_method='HALF-UP')
                else:
                    number_of_days = 1 # If not supposed to work in calendar attendances, then there
                                       # are not time offs
                work_data[('full', work_entry_type_id)][0] += number_of_days
                work_data[('full', work_entry_type_id)][1] += duration_sum
            else:
                work_data[('half', work_entry_type_id)][0] += 1
                work_data[('half', work_entry_type_id)][1] += duration_sum

        # Second, find work entry that exceeds interval and compute right duration.
        work_entries = self.env['hr.work.entry'].search(self._get_work_hours_domain(date_from, date_to, domain=domain, inside=False))

        for work_entry in work_entries:
            date_start = max(date_from, work_entry.date_start)
            date_stop = min(date_to, work_entry.date_stop)
            if work_entry.work_entry_type_id.is_leave:
                contract = work_entry.contract_id
                calendar = contract.resource_calendar_id
                employee = contract.employee_id
                contract_data = employee._get_work_days_data_batch(
                    date_start, date_stop, compute_leaves=False, calendar=calendar
                )[employee.id]
                if float_compare(contract_data.get('hours', 0), number_of_hours_full_day, 2) != -1:
                    work_data[('full', work_entry.work_entry_type_id.id)][0] += 1
                    work_data[('full', work_entry.work_entry_type_id.id)][1] += work_entry.duration
                else:
                    work_data[('half', work_entry.work_entry_type_id.id)][1] += work_entry.duration
            else:
                dt = date_stop - date_start
                work_data[('half', work_entry.work_entry_type_id.id)] += dt.days * 24 + dt.seconds / 3600  # Number of hours
        return work_data

    # override to add work_entry_type from leave
    def _get_leave_work_entry_type_dates(self, leave, date_from, date_to, employee):
        result = super()._get_leave_work_entry_type_dates(leave, date_from, date_to, employee)
        if not self._is_struct_from_country('BE'):
            return result

        # The public holidays are paid only during the 14 first days of unemployment
        if result.code == "LEAVE500":
            unemployed_less_than_14_days_before = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date_to', '>=', leave.date_from + relativedelta(days=-14)),
                ('date_from', '<=', leave.date_from),
                ('holiday_status_id.work_entry_type_id.code', 'in', ['LEAVE6666', 'LEAVE6665']),
                ('state', '=', 'validate'),
            ], order="date_from asc")
            if unemployed_less_than_14_days_before:
                is_unemployed = True
                for offset in range(15):
                    day = leave.date_from + relativedelta(days=-offset)
                    if all(l.date_from > day or l.date_to < day for l in unemployed_less_than_14_days_before):
                        is_unemployed = False
                if is_unemployed:
                    return unemployed_less_than_14_days_before[0].holiday_status_id.work_entry_type_id

        # The public holidays are paid only during the period of 30 days following the start of the
        # suspension of the employment contract due to illness or accident, work accident or
        # occupational disease, pregnancy or childbirth leave, strike or lockout;
        if result.code == "LEAVE500":
            absent_less_than_X_days_before = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date_to', '>=', leave.date_from + relativedelta(days=-30)),
                ('date_from', '<=', leave.date_from),
                ('holiday_status_id.work_entry_type_id.code', 'in', ['LEAVE210', 'LEAVE220', 'LEAVE230', 'LEAVE115', 'LEAVE281']),
                ('state', '=', 'validate'),
            ], order="date_from asc")
            if absent_less_than_X_days_before:
                is_absent = True
                # Special case for credit-times
                # If time credit duration X is:
                # X < 1 month -> Unpaid
                # 1 <= X < 3 months -> Paid the first 14 days
                # X >= 3 months -> Paid the first 30 days
                # Alway unpaid for full time credit time
                paid_duration = 30
                if self.time_credit:
                    if not self.work_time_rate:
                        return absent_less_than_X_days_before[0].holiday_status_id.work_entry_type_id
                    duration_start = self._get_occupation_dates()[0][1]
                    duration_stop = leave.date_from.date()
                    number_of_months = (duration_stop.year - duration_start.year) * 12 + (duration_stop.month - duration_start.month)
                    if number_of_months < 1:
                        return absent_less_than_X_days_before[0].holiday_status_id.work_entry_type_id
                    if number_of_months < 3:
                        paid_duration = 14
                        absent_less_than_X_days_before = absent_less_than_X_days_before.filtered_domain([
                            ('date_to', '>=', leave.date_from + relativedelta(days=-paid_duration))])
                for offset in range(paid_duration):
                    day = leave.date_from + relativedelta(days=-offset)
                    if all(l.date_from > day or l.date_to < day for l in absent_less_than_X_days_before):
                        is_absent = False
                if is_absent:
                    return absent_less_than_X_days_before[0].holiday_status_id.work_entry_type_id

        # The salary is not guaranteed after 30 calendar days of sick leave (it means from the 31th
        # day of sick leave)
        # LEAVE110 = classic sick leave
        if result.code == "LEAVE110":
            sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
            partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')
            long_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_long_sick')
            sick_work_entry_types = sick_work_entry_type + partial_sick_work_entry_type + long_sick_work_entry_type
            sick_less_than_30days_before = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date_to', '>=', leave.date_from + relativedelta(days=-30)),
                ('date_from', '<=', leave.holiday_id.date_from),
                ('holiday_status_id.work_entry_type_id', 'in', sick_work_entry_types.ids),
                ('state', '=', 'validate'),
                ('id', '!=', leave.holiday_id.id),
            ], order="date_from asc")
            if not leave.holiday_id:
                return result
            # The current time off is longer than 30 days -> Partial Time Off
            if (date_from - leave.holiday_id.date_from).days + 1 > 30:
                return partial_sick_work_entry_type
            # No previous sick time off -> Sick Time Off
            if not sick_less_than_30days_before:
                return result
            # If there a gap of more than 15 days between 2 sick time offs,
            # the salary is guaranteed -> Sick Time Off
            all_leaves = sick_less_than_30days_before | leave.holiday_id
            for i in range(len(all_leaves) - 1):
                if (all_leaves[i+1].date_from - all_leaves[i].date_to).days > 15:
                    return result
            # No gap and more than 30 calendar days -> Partial Time Off
            # only the first 30 calendar days of sickness are covered by guaranteed wages, which
            # does not mean 30 days of sickness.
            # Example :
            # - Sick from September 1 to 7 included
            # - Rework from 8 to 14
            # - Re-ill from September 15 to October 13
            # Here, are therefore covered by guaranteed wages:
            # from 01 to 07/09 (i.e. 7 days)
            # from 15/09 to 07/10 (i.e. the balance of 23 days).
            # In fact, we and public holidays which fall within a period covered by a medical
            # certificate are taken into account in the period of 30 calendar days of guaranteed
            # salary.
            # Sick days from 08/10 are therefore not covered by the employer (mutual from 08/10
            # to 13/10).
            total_sick_days = sum([(l.date_to - l.date_from).days + 1 for l in sick_less_than_30days_before])
            this_leave_current_duration = (date_from - leave.holiday_id.date_from).days + 1
            # Include off days (eg: weekends) that are not convered by time off
            # in case the sick time off is split and not covering the whole
            # interval
            min_date_from = min(sick_less_than_30days_before.mapped('date_from'))
            max_date_to = leave.holiday_id.date_to
            employee_contracts = employee._get_contracts(min_date_from, max_date_to, states=['open', 'close'])
            work_hours_data_by_calendar = {
                c.resource_calendar_id: [work_day for work_day, work_hours in employee.with_context(
                    compute_leaves=False).list_work_time_per_day(min_date_from, max_date_to, c.resource_calendar_id)]
                for c in employee_contracts}
            effective_worked_days = {
                calendar: [
                    work_day for work_day in work_days \
                    if all(work_day < l.date_from.date() or work_day > l.date_to.date() for l in sick_less_than_30days_before + leave.holiday_id)
                ] for calendar, work_days in work_hours_data_by_calendar.items()
            }
            uncovered_off_days = 0
            last_seen_work_day = (min_date_from + relativedelta(days=-1)).date()
            last_seen_off_day = min_date_from.date()
            for day in rrule(DAILY, min_date_from, until=max_date_to):
                day = day.date()
                if day >= date_from.date():
                    continue
                day_contract = employee_contracts.filtered(lambda c: c.date_start <= day and (not c.date_end or c.date_end >= day))
                if day in effective_worked_days[day_contract.resource_calendar_id]:
                    last_seen_work_day = day
                    continue
                if all(day < l.date_from.date() or day > l.date_to.date() for l in sick_less_than_30days_before + leave.holiday_id):
                    if day not in work_hours_data_by_calendar[day_contract.resource_calendar_id]:
                        # Backward check, only count the day if only time off before
                        # (eg: Avoid counting Sat/Sun if worked the days before)
                        if last_seen_work_day > last_seen_off_day:
                            continue
                        uncovered_off_days += 1
                else:
                    last_seen_off_day = day
            if total_sick_days + this_leave_current_duration + uncovered_off_days > 30:
                return partial_sick_work_entry_type
        return result

    def _get_bypassing_work_entry_type_codes(self):
        return super()._get_bypassing_work_entry_type_codes() + [
            'LEAVE280', # Long term sick
            'LEAVE281', # Partial Incapacity
            # 'LEAVE110', # Sick Leave - Actually Sick Leave < Public Time Off
                          # If the employee does not have to work on a public
                          # holiday but falls ill when he could have benefited
                          # from a well-deserved day off, he is not entitled to
                          # a guaranteed salary but to remuneration in accordance
                          # with the days holidays. In fact, the employee is
                          # entitled to remuneration for each public holiday falling
                          # within 30 calendar days of the onset of his illness.
        ]

    def _is_same_occupation(self, contract):
        self.ensure_one()
        res = super()._is_same_occupation(contract)
        time_credit = self.time_credit
        time_credit_type = self.time_credit_type_id
        return res and time_credit == contract.time_credit and (not time_credit or (time_credit_type == contract.time_credit_type_id))

    def _create_credit_time_next_activity(self):
        self.ensure_one()
        part_time_link = "https://www.socialsecurity.be/site_fr/employer/applics/elo/index.htm"
        part_time_link = '<a href="%s" target="_blank">%s</a>' % (part_time_link, part_time_link)
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            note=_('Part Time of %s must be stated at %s.',
                   self.employee_id.name,
                   part_time_link),
            user_id=self.hr_responsible_id.id or self.env.user.id,
        )

    def _create_dimona_next_activity(self):
        self.ensure_one()
        dimona_link = "https://www.socialsecurity.be/site_fr/employer/applics/dimona/index.htm"
        dimona_link = '<a href="%s" target="_blank">%s</a>' % (dimona_link, dimona_link)
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            note=_('State the Dimona at %s to declare the arrival of %s.',
                   dimona_link,
                   self.employee_id.name),
            user_id=self.hr_responsible_id.id or self.env.user.id,
            summary='Dimona',
            )

    def _trigger_l10n_be_next_activities(self):
        employees_with_contract_domain = [
            ('state', 'in', ('open', 'close')),
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('id', 'not in', self.ids),
        ]
        employees_already_started = self.env['hr.contract'].search(employees_with_contract_domain).mapped('employee_id')
        for contract in self:
            if not contract._is_struct_from_country('BE'):
                continue
            if contract.time_credit:
                contract._create_credit_time_next_activity()
            if contract.employee_id not in employees_already_started:
                contract._create_dimona_next_activity()

    def _get_contract_insurance_amount(self, name):
        self.ensure_one()
        if name == 'hospital':
            return self._get_hospital_insurance_amount()
        if name == 'ambulatory':
            return self.l10n_be_ambulatory_insurance_amount
        if name == 'group':
            return self.l10n_be_group_insurance_amount * (1 + 4.4 / 100.0)
        return 0.0

    def _get_hospital_insurance_amount(self):
        self.ensure_one()
        return self.insurance_amount

    def write(self, vals):
        res = super(HrContract, self).write(vals)
        if vals.get('state') == 'open':
            self._trigger_l10n_be_next_activities()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        contracts.filtered(lambda c: c.state == 'open')._trigger_l10n_be_next_activities()
        return contracts

    def _get_fields_that_recompute_we(self):
        return super()._get_fields_that_recompute_we() + [
            'time_credit',
            'time_credit_type_id',
            'standard_calendar_id',
        ]

    def _get_fields_that_recompute_payslip(self):
        # Returns the fields that should recompute the payslip
        return super()._get_fields_that_recompute_payslip() + [
            'representation_fees',
            'ip',
            'ip_wage_rate',
            'mobile',
            'internet',
            'transport_mode_car',
            'transport_mode_private_car',
            'transport_mode_train',
            'transport_mode_public',
            'train_transport_employee_amount',
            'public_transport_employee_amount',
            'km_home_work',
            'has_laptop',
            'meal_voucher_amount'
            'work_time_rate',
            'fiscal_voluntarism',
            'fiscal_voluntary_rate',
            'no_onss',
            'no_withholding_taxes',
        ]

    def action_work_schedule_change_wizard(self):
        self.ensure_one()
        if self.state not in ('draft', 'open'):
            return False
        action = self.env['ir.actions.actions']._for_xml_id('l10n_be_hr_payroll.schedule_change_wizard_action')
        action['context'] = {'active_id': self.id}
        return action
