# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from functools import reduce

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    niss = fields.Char(
        'NISS Number', compute="_compute_niss", store=True, readonly=False,
        groups="hr.group_hr_user", tracking=True)
    spouse_fiscal_status = fields.Selection([
        ('without_income', 'Without Income'),
        ('high_income', 'With High income'),
        ('low_income', 'With Low Income'),
        ('low_pension', 'With Low Pensions'),
        ('high_pension', 'With High Pensions')
    ], string='Tax status for spouse', groups="hr.group_hr_user", default='without_income', required=False, tracking=True)
    spouse_fiscal_status_explanation = fields.Char(compute='_compute_spouse_fiscal_status_explanation')
    disabled = fields.Boolean(string="Disabled", help="If the employee is declared disabled by law", groups="hr.group_hr_user", tracking=True)
    disabled_spouse_bool = fields.Boolean(string='Disabled Spouse', help='if recipient spouse is declared disabled by law', groups="hr.group_hr_user", tracking=True)
    disabled_children_bool = fields.Boolean(string='Disabled Children', help='if recipient children is/are declared disabled by law', groups="hr.group_hr_user", tracking=True)
    disabled_children_number = fields.Integer('Number of disabled children', groups="hr.group_hr_user", tracking=True)
    dependent_children = fields.Integer(compute='_compute_dependent_children', string='Considered number of dependent children', groups="hr.group_hr_user", tracking=True)
    l10n_be_dependent_children_attachment = fields.Integer(
        string="# dependent children for salary attachement", groups="hr.group_hr_user", tracking=True,
        help="""To benefit from this increase in the elusive or non-transferable quotas, the worker whose remuneration is subject to seizure or transfer, must declare it using a form, the model of which has been published in the Belgian Official Gazette. of 30 November 2006.

He must attach to this form the documents establishing the reality of the charge invoked.

Source: Opinion on the indexation of the amounts set in Article 1, paragraph 4, of the Royal Decree of 27 December 2004 implementing Articles 1409, § 1, paragraph 4, and 1409, § 1 bis, paragraph 4 , of the Judicial Code relating to the limitation of seizure when there are dependent children, MB, December 13, 2019.""")
    other_dependent_people = fields.Boolean(string="Other Dependent People", help="If other people are dependent on the employee", groups="hr.group_hr_user", tracking=True)
    other_senior_dependent = fields.Integer('# seniors (>=65)', help="Number of seniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user", tracking=True)
    other_disabled_senior_dependent = fields.Integer('# disabled seniors (>=65)', groups="hr.group_hr_user", tracking=True)
    other_juniors_dependent = fields.Integer('# people (<65)', help="Number of juniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user", tracking=True)
    other_disabled_juniors_dependent = fields.Integer('# disabled people (<65)', groups="hr.group_hr_user", tracking=True)
    dependent_seniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent seniors", groups="hr.group_hr_user")
    dependent_juniors = fields.Integer(compute='_compute_dependent_people', string="Considered number of dependent juniors", groups="hr.group_hr_user")

    start_notice_period = fields.Date("Start notice period", groups="hr.group_hr_user", copy=False, tracking=True)
    end_notice_period = fields.Date("End notice period", groups="hr.group_hr_user", copy=False, tracking=True)
    first_contract_in_company = fields.Date("First contract in company", groups="hr.group_hr_user", copy=False)

    certificate = fields.Selection(selection_add=[('civil_engineer', 'Master: Civil Engineering')])
    l10n_be_scale_seniority = fields.Integer(string="Seniority at Hiring", groups="hr.group_hr_user", tracking=True)

    # The attestation for the year of the first contract date
    first_contract_year_n = fields.Char(compute='_compute_first_contract_year')
    first_contract_year_n_plus_1 = fields.Char(compute='_compute_first_contract_year')
    l10n_be_holiday_pay_to_recover_n = fields.Float(
        string="Simple Holiday Pay to Recover (N)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer to recover.")
    l10n_be_holiday_pay_number_of_days_n = fields.Float(
        string="Number of days to recover (N)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Number of days on which you should recover the holiday pay.")
    l10n_be_holiday_pay_recovered_n = fields.Float(
        string="Recovered Simple Holiday Pay (N)", tracking=True,
        compute='_compute_l10n_be_holiday_pay_recovered', groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer already recovered.")
    double_pay_line_n_ids = fields.Many2many(
        'l10n.be.double.pay.recovery.line', 'double_pay_n_rel' 'employee_id', 'double_pay_line_n_ids',
        compute='_compute_from_double_pay_line_ids', readonly=False,
        inverse='_inverse_double_pay_line_n_ids',
        string='Previous Occupations (N)', groups="hr_payroll.group_hr_payroll_user")

    # The attestation for the previous year of the first contract date
    first_contract_year_n1 = fields.Char(compute='_compute_first_contract_year')
    l10n_be_holiday_pay_to_recover_n1 = fields.Float(
        string="Simple Holiday Pay to Recover (N-1)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer to recover.")
    l10n_be_holiday_pay_number_of_days_n1 = fields.Float(
        string="Number of days to recover (N-1)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Number of days on which you should recover the holiday pay.")
    l10n_be_holiday_pay_recovered_n1 = fields.Float(
        string="Recovered Simple Holiday Pay (N-1)", tracking=True,
        compute='_compute_l10n_be_holiday_pay_recovered', groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer already recovered.")
    double_pay_line_n1_ids = fields.Many2many(
        'l10n.be.double.pay.recovery.line', 'double_pay_n1_rel' 'employee_id', 'double_pay_line_n1_ids',
        compute='_compute_from_double_pay_line_ids', readonly=False,
        inverse='_inverse_double_pay_line_n1_ids',
        string='Previous Occupations (N-1)', groups="hr_payroll.group_hr_payroll_user")
    first_contract_year = fields.Integer(compute='_compute_first_contract_year')
    double_pay_line_ids = fields.One2many(
        'l10n.be.double.pay.recovery.line', 'employee_id',
        string='Previous Occupations', groups="hr_payroll.group_hr_payroll_user")

    @api.constrains('children', 'disabled_children_number',
                    'other_senior_dependent', 'other_disabled_senior_dependent',
                    'other_juniors_dependent', 'other_disabled_juniors_dependent',
                    'l10n_be_dependent_children_attachment')
    def _check_dependent(self):
        validation_error_message = []
        for employee in self:
            if (employee.children < 0 or employee.disabled_children_number < 0 or
               employee.other_senior_dependent < 0 or employee.other_disabled_senior_dependent < 0 or
               employee.other_juniors_dependent < 0 or employee.other_disabled_juniors_dependent < 0 or
               employee.l10n_be_dependent_children_attachment < 0):
                validation_error_message.append(_("Count of dependent people/children or disabled dependent people/children must be positive."))
            if ((employee.disabled_children_number > 0 and employee.disabled_children_number > employee.children) or
               (employee.other_disabled_senior_dependent > 0 and employee.other_disabled_senior_dependent > employee.other_senior_dependent) or
               (employee.other_disabled_juniors_dependent > 0 and employee.other_disabled_juniors_dependent > employee.other_juniors_dependent) or
               (employee.l10n_be_dependent_children_attachment > 0 and employee.l10n_be_dependent_children_attachment > employee.children)):
                validation_error_message.append(_("Count of disabled dependent people/children must be less or equal to the number of dependent people/children."))
            if validation_error_message:
                raise ValidationError("\n".join(validation_error_message))

    @api.depends('first_contract_date')
    def _compute_first_contract_year(self):
        current_year = fields.Datetime.today().date().year
        for employee in self:
            year = employee.first_contract_date.year if employee.first_contract_date else current_year
            employee.first_contract_year = year
            employee.first_contract_year_n = year
            employee.first_contract_year_n1 = year - 1
            employee.first_contract_year_n_plus_1 = year + 1

    def _compute_from_double_pay_line_ids(self):
        for employee in self:
            year = employee.first_contract_year
            employee.double_pay_line_n_ids = employee.double_pay_line_ids.filtered(lambda d: d.year == year)
            employee.double_pay_line_n1_ids = employee.double_pay_line_ids.filtered(lambda d: d.year == year - 1)

    def _inverse_double_pay_line_n_ids(self):
        for employee in self:
            year = employee.first_contract_year
            to_be_deleted = employee.double_pay_line_ids.filtered(lambda d: d.year == year) - employee.double_pay_line_n_ids
            employee.double_pay_line_ids.filtered(lambda d: d.id in to_be_deleted.ids).unlink()
            employee.double_pay_line_ids |= employee.double_pay_line_n_ids

    def _inverse_double_pay_line_n1_ids(self):
        for employee in self:
            year = employee.first_contract_year
            to_be_deleted = employee.double_pay_line_ids.filtered(lambda d: d.year == year - 1) - employee.double_pay_line_n1_ids
            employee.double_pay_line_ids.filtered(lambda d: d.id in to_be_deleted.ids).unlink()
            employee.double_pay_line_ids |= employee.double_pay_line_n1_ids

    @api.constrains('start_notice_period', 'end_notice_period')
    def _check_notice_period(self):
        for employee in self:
            if employee.start_notice_period and employee.end_notice_period and employee.start_notice_period > employee.end_notice_period:
                raise ValidationError(_('The employee start notice period should be set before the end notice period'))

    def _compute_l10n_be_holiday_pay_recovered(self):
        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', self.ids),
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id),
            ('company_id', '=', self.env.company.id),
            ('state', 'in', ['done', 'paid']),
        ])
        line_values = payslips._get_line_values(['HolPayRecN', 'HolPayRecN1'])
        payslips_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in payslips:
            payslips_by_employee[payslip.employee_id] |= payslip

        for employee in self:
            employee_payslips = payslips_by_employee[employee]
            employee.l10n_be_holiday_pay_recovered_n = - sum(line_values['HolPayRecN'][p.id]['total'] for p in employee_payslips)
            employee.l10n_be_holiday_pay_recovered_n1 = - sum(line_values['HolPayRecN1'][p.id]['total'] for p in employee_payslips)

    def _compute_spouse_fiscal_status_explanation(self):
        low_income_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('spouse_low_income_threshold')
        other_income_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('spouse_other_income_threshold')
        for employee in self:
            employee.spouse_fiscal_status_explanation = _("""- Without Income: The spouse of the income recipient has no professional income.\n
- High income: The spouse of the recipient of the income has professional income, other than pensions, annuities or similar income, which exceeds %s€ net per month.\n
- Low Income: The spouse of the recipient of the income has professional income, other than pensions, annuities or similar income, which does not exceed %s€ net per month.\n
- Low Pensions: The spouse of the beneficiary of the income has professional income which consists exclusively of pensions, annuities or similar income and which does not exceed %s€ net per month.\n
- High Pensions: The spouse of the beneficiary of the income has professional income which consists exclusively of pensions, annuities or similar income and which exceeds %s€ net per month.""", low_income_threshold, low_income_threshold, other_income_threshold, other_income_threshold)

    @api.depends('identification_id')
    def _compute_niss(self):
        characters = dict.fromkeys([',', '.', '-', ' '], '')
        for employee in self:
            if employee.identification_id and not employee.niss and employee.company_country_code == 'BE':
                employee.niss = reduce(lambda a, kv: a.replace(*kv), characters.items(), employee.identification_id)

    @api.model
    def _validate_niss(self, niss):
        try:
            test = niss[:-2]
            if test[0] in ['0', '1', '2', '3', '4', '5']:  # Should be good for several years
                test = '2%s' % test
            checksum = int(niss[-2:])
            if checksum != (97 - int(test) % 97):
                raise Exception()
            return True
        except Exception:
            return False

    def _is_niss_valid(self):
        # The last 2 positions constitute the check digit. This check digit is
        # a sequence of 2 digits forming a number between 01 and 97. This number is equal to 97
        # minus the remainder of the division by 97 of the number formed:
        # - either by the first 9 digits of the national number for people born before the 1st
        # January 2000.
        # - either by the number 2 followed by the first 9 digits of the national number for people
        # born after December 31, 1999.
        # (https://fr.wikipedia.org/wiki/Num%C3%A9ro_de_registre_national)
        self.ensure_one()
        niss = self.niss
        if not niss or len(niss) != 11:
            return False
        return self._validate_niss(niss)

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

    @api.model
    def _get_invalid_niss_employee_ids(self):
        # as we do not store if the niss is valid or not it's not possible to fetch all the employees directly
        # use sql and manually filter the employees

        # return nothing if user has no right to either employee or bank partner
        try:
            self.check_access_rights('read')
            # niss field is for this group only
            if not self.user_has_groups('hr.group_hr_user'):
                raise AccessError()
        except AccessError:
            return []

        self.env.cr.execute('''
            SELECT emp.id,
                   emp.niss
              FROM hr_employee emp
              JOIN hr_contract con
              ON con.id = emp.contract_id
              AND con.state in ('open', 'close')
             WHERE emp.company_id IN %s
               AND emp.employee_type IN ('employee', 'student')
               AND emp.active=TRUE
        ''', (tuple(c.id for c in self.env.companies if c.country_id.code == 'BE'),))
        return [row['id'] for row in self.env.cr.dictfetchall() if not row['niss'] or not self._validate_niss(row['niss'])]
