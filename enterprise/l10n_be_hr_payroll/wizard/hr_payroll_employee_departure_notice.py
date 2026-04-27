# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from datetime import datetime, timedelta

from dateutil import rrule
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployeeDepartureNotice(models.TransientModel):
    _name = 'hr.payslip.employee.depature.notice'
    _description = 'Manage the Employee Departure - Notice Duration'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id'), domain="[('company_id', 'in', allowed_company_ids)]")
    departure_date = fields.Date(string='Departure Date', default=fields.Date.context_today, required=True)
    leaving_type_id = fields.Many2one('hr.departure.reason', string='Departure Reason', required=True)
    departure_reason_code = fields.Integer(related='leaving_type_id.reason_code')

    start_notice_period = fields.Date(
        string='Start Notice Period',
        help='First monday from the departure date (or the following open day if it is a public holiday).',
        compute='_compute_start_notice_period')
    end_notice_period = fields.Date('End Notice Period', compute='_compute_end_notice_period', store=True, readonly=False)
    departure_description = fields.Char('Departure Description', required=True)
    oldest_contract_id = fields.Many2one('hr.contract', string='Oldest Contract', compute='_compute_oldest_contract_id')
    first_contract = fields.Date(
        string='In the Company Since',
        help='First contract start date.',
        compute='_compute_oldest_contract_id')
    seniority_description = fields.Char(string='Seniority', compute='_compute_seniority_description')

    salary_december_2013 = fields.Selection([
        ('inferior', 'Gross annual salary < 32.254 €'),
        ('superior', 'Gross annual salary > 32.254 €')
        ], string='Gross Annual Salary as of December 31, 2013', required=True, default='superior')
    salary_visibility = fields.Boolean('Salary as of December 2013')
    notice_duration_month_before_2014 = fields.Integer('Notice Duration in month', compute='_notice_duration')
    notice_duration_week_after_2014 = fields.Integer('Notice Duration in weeks', compute='_notice_duration')
    actual_notice_duration = fields.Integer('Actual Notice Duration', compute='_compute_actual_notice_duration')

    notice_respect = fields.Selection([
        ('with', 'Employee works during his notice period'),
        ('partial', 'Employee works partially during his notice period'),
        ('without', "Employee doesn't work during his notice period"),
        ], string='Respect of the notice period', required=True, default='with',
        help='Decides whether the employee will still work during his notice period or not.')

    @api.onchange('leaving_type_id')
    def _onchange_leaving_type_id(self):
        self.notice_respect = 'with'

    @api.depends('employee_id')
    def _compute_oldest_contract_id(self):
        """ get the oldest contract """
        for notice in self:
            pfi = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_pfi')
            notice.oldest_contract_id = self.env['hr.contract'].search([
                ('employee_id', '=', notice.employee_id.id),
                ('state', '!=', 'cancel'),
                ('contract_type_id', '!=', pfi.id)
            ], order='date_start asc', limit=1)
            notice.first_contract = notice.oldest_contract_id.date_start

    @api.depends('start_notice_period', 'end_notice_period')
    def _compute_actual_notice_duration(self):
        for notice in self:
            weeks = rrule.rrule(rrule.WEEKLY, dtstart=notice.start_notice_period, until=notice.end_notice_period)
            notice.actual_notice_duration = weeks.count()

    @api.depends('first_contract', 'departure_date')
    def _compute_seniority_description(self):
        for notice in self:
            difference = relativedelta(notice.departure_date, notice.first_contract)
            if difference.years == 0:
                notice.seniority_description = _('%(months)s months', months=difference.months)
            else:
                notice.seniority_description = _('%(years)s years and %(months)s months', months=difference.months, years=difference.years)

    @api.depends('departure_date', 'notice_respect', 'departure_reason_code', 'oldest_contract_id')
    def _compute_start_notice_period(self):
        public_holiday_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday')
        for notice in self:
            if not notice.oldest_contract_id or notice.notice_respect == 'without' or notice.departure_reason_code in (350, 351):
                notice.start_notice_period = notice.departure_date
            elif notice.departure_reason_code == 342:
                # We can only take the next monday that has at least 3 calendar days (Monday to Saturday except public
                # holidays) between the departure date and the start of the notice period
                public_leaves = self.employee_id.contract_id.resource_calendar_id.global_leave_ids.filtered(
                    lambda l: l.work_entry_type_id == public_holiday_type)
                public_holidays_dates = (d.date() for d in public_leaves.mapped('date_from'))
                calendar_days = 0
                current_date = notice.departure_date + relativedelta(days=1)
                while calendar_days < 3:
                    if current_date not in public_holidays_dates and current_date.weekday() != 6:
                        calendar_days += 1
                    current_date = current_date + relativedelta(days=1)
                notice.start_notice_period = current_date + relativedelta(days=7 - current_date.weekday())
            else:
                notice.start_notice_period = notice.departure_date + relativedelta(days=7 - notice.departure_date.weekday())

    @api.depends('notice_duration_month_before_2014', 'notice_duration_week_after_2014', 'start_notice_period', 'notice_respect', 'departure_date', 'departure_reason_code', 'oldest_contract_id')
    def _compute_end_notice_period(self):
        for notice in self:
            if not notice.oldest_contract_id or notice.notice_respect == 'without':
                notice.end_notice_period = notice.departure_date
            elif notice.start_notice_period:
                if notice.departure_reason_code in [350, 351]:
                    notice.end_notice_period = notice.start_notice_period
                else:
                    months_to_weeks = notice.notice_duration_month_before_2014 / 3.0 * 13
                    notice.end_notice_period = notice.start_notice_period + timedelta(weeks=months_to_weeks + notice.notice_duration_week_after_2014, days=-1)

    @api.depends('first_contract', 'leaving_type_id', 'salary_december_2013', 'start_notice_period', 'oldest_contract_id')
    def _notice_duration(self):
        first_2014 = datetime(2014, 1, 1)
        departure_reasons = self.env['hr.departure.reason']._get_default_departure_reasons()
        for notice in self:
            if not notice.oldest_contract_id:
                notice.salary_visibility = False
                notice.notice_duration_month_before_2014 = 0
                notice.notice_duration_week_after_2014 = 0
                continue
            if notice._get_years(relativedelta(first_2014, notice.first_contract)) < 0:
                first_day_since_2014 = notice.first_contract
            else:
                first_day_since_2014 = first_2014
            period_since_2014 = relativedelta(notice.start_notice_period, first_day_since_2014)
            difference_in_years = notice._get_years(relativedelta(datetime(2013, 12, 31),
                notice.first_contract))
            if notice.leaving_type_id.reason_code == departure_reasons['fired']:
                # Part I
                if difference_in_years > 0:
                    notice.salary_visibility = True
                    if notice.salary_december_2013 == 'inferior':
                        notice.notice_duration_month_before_2014 = int(math.ceil(difference_in_years / 5.0) * 3.0)
                    else:
                        notice.notice_duration_month_before_2014 = max(int(math.ceil(difference_in_years)), 3)
                else:
                    notice.salary_visibility = False
                    notice.notice_duration_month_before_2014 = 0
                # Part II
                notice.notice_duration_week_after_2014 = notice._find_week(
                    period_since_2014.months + period_since_2014.years * 12, 'fired')
            elif notice.leaving_type_id.reason_code == departure_reasons['resigned']:
                notice.salary_visibility = False
                notice.notice_duration_month_before_2014 = 0
                notice.notice_duration_week_after_2014 = notice._find_week(
                    period_since_2014.months + period_since_2014.years * 12, 'resigned')
            elif notice.leaving_type_id.reason_code == departure_reasons['retired']:
                notice.salary_visibility = False
                notice.notice_duration_month_before_2014 = 0
                notice.notice_duration_week_after_2014 = notice._find_week(
                    period_since_2014.months + period_since_2014.years * 12, 'resigned')
            else:
                notice.salary_visibility = False
                notice.notice_duration_month_before_2014 = 0
                notice.notice_duration_week_after_2014 = 0

    def _get_years(self, date):
        return date.years + date.months / 12 + date.days / 365

    def _find_week(self, duration_worked_month, leaving_type_id):
        if leaving_type_id == 'resigned':
            duration_notice = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_be_duration_notice_resigned', self.departure_date)
        else:
            duration_notice = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_be_duration_notice_fired', self.departure_date)
            # Once you reach 24 years (288 months) of seniority,
            # you have one more week in the notice period per year
            # starting at 66 weeks for the 24th year.
            threshold, duration = duration_notice[-1]
            if duration_worked_month >= threshold:
                return duration + 1 + duration_worked_month // 12 - threshold / 12
        for seniority_upper_bound, duration in duration_notice:
            if duration_worked_month < seniority_upper_bound:
                return duration
        return 0  # Should not happen but makes python happy

    def validate_termination(self):
        self.employee_id.write({
            'departure_reason_id': self.leaving_type_id,
            'departure_description': self.departure_description,
            'start_notice_period': self.start_notice_period,
            'end_notice_period': self.end_notice_period,
            'departure_date': self.end_notice_period,
            'first_contract_in_company': self.first_contract
        })
        if self.employee_id.contract_id:
            self.employee_id.contract_id.write({
                'date_end': self.end_notice_period,
            })

    def _get_input_type(self, name, cp='cp200'):
        input_type = self.env.ref('l10n_be_hr_payroll.%s_other_input_%s' % (cp, name), raise_if_not_found=False)
        return input_type.id if input_type else False

    def _create_input(self, payslip_id, sequence, input_type, amount, contract_id):
        input_type_id = self._get_input_type(input_type)
        if not input_type_id:
            return
        self.env['hr.payslip.input'].create({
            'payslip_id': payslip_id,
            'sequence': sequence,
            'input_type_id': input_type_id,
            'amount': amount,
            'contract_id': contract_id
        })

    def compute_termination_fee(self):
        self.validate_termination()
        struct_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_termination_fees')

        last_contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '!=', 'cancel')
        ], order='date_start desc', limit=1)

        termination_payslip = self.env['hr.payslip'].create({
            'name': '%s - %s' % (struct_id.payslip_name, self.employee_id.legal_name),
            'employee_id': self.employee_id.id,
            'date_from': self.start_notice_period,
            'date_to': self.start_notice_period,
            'contract_id': last_contract.id,
            'struct_id': struct_id.id,
        })
        termination_payslip.worked_days_line_ids = [(5, 0, 0)]

        contract = termination_payslip.contract_id
        payslip_id = termination_payslip.id

        weeks = self.notice_duration_week_after_2014
        if self.notice_respect == 'partial':
            weeks -= self.actual_notice_duration

        self._create_input(payslip_id, 1, 'months', self.notice_duration_month_before_2014, contract.id)
        self._create_input(payslip_id, 2, 'weeks', weeks, contract.id)
        self._create_input(payslip_id, 3, 'days', 0, contract.id)
        self._create_input(payslip_id, 4, 'unreasonable_dismissal', 0, contract.id)
        self._create_input(payslip_id, 5, 'non_respect_motivation', 0, contract.id)
        self._create_input(payslip_id, 10, 'yearend_bonus', contract._get_contract_wage(), contract.id)
        self._create_input(payslip_id, 11, 'residence', 0, contract.id)
        self._create_input(payslip_id, 12, 'expatriate', 0, contract.id)
        self._create_input(payslip_id, 13, 'variable_salary', termination_payslip._get_last_year_average_variable_revenues() * 12, contract.id)
        self._create_input(payslip_id, 14, 'benefit_in_kind', 0, contract.id)
        self._create_input(payslip_id, 15, 'hospital_insurance', contract._get_contract_insurance_amount('hospital'), contract.id)
        self._create_input(payslip_id, 15, 'ambulatory_insurance', contract._get_contract_insurance_amount('ambulatory'), contract.id)
        self._create_input(payslip_id, 16, 'group_insurance', contract._get_contract_insurance_amount('group'), contract.id)
        self._create_input(payslip_id, 17, 'stock_option', termination_payslip._get_last_year_average_warrant_revenues(), contract.id)
        self._create_input(payslip_id, 18, 'specific_rules', 0, contract.id)
        self._create_input(payslip_id, 19, 'other', 0, contract.id)
        termination_payslip.compute_sheet()
        return {
            'name': _('Termination'),
            'view_mode': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'res_id': termination_payslip.id,
        }
