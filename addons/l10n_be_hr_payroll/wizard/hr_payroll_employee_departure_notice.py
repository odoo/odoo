# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class HrPayslipEmployeeDepartureNotice(models.TransientModel):
    _name = 'hr.payslip.employee.depature.notice'
    _description = 'Manage the Employee Departure - Notice Duration'

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id'))
    leaving_type = fields.Selection([
            ('fired', 'Fired'),
            ('resigned', 'Resigned'),
            ('retired', 'Retired')
        ], string='Leaving Type', required=True, default='fired')
    start_notice_period = fields.Date('Start notice period', required=True, default=fields.Date.context_today)
    end_notice_period = fields.Date('End notice period', required=True)

    oldest_contract_id = fields.Many2one('hr.contract', string='Oldest Contract', compute='_compute_oldest_contract_id')
    first_contract = fields.Date('First contract in company', required=True)

    salary_december_2013 = fields.Selection([
            ('inferior', 'Gross annual salary < 32.254 €'),
            ('superior', 'Gross annual salary > 32.254 €')
        ], string='Gross Annual Salary as of December 31, 2013', required=True, default='superior')
    salary_visibility = fields.Boolean('Salary as of December 2013')
    notice_duration_month_before_2014 = fields.Integer('Notice Duration in month', compute='_notice_duration')
    notice_duration_week_after_2014 = fields.Integer('Notice Duration in weeks', compute='_notice_duration')

    notice_respect = fields.Selection([
            ('with', 'Employee will leave after notice period'),
            ('without', 'Employee will leave before notice period')
        ], string='Respect of the notice period', required=True, default='with')

    @api.one
    @api.depends('employee_id')
    def _compute_oldest_contract_id(self):
        """ get the oldest contract """
        self.oldest_contract_id = self.env['hr.contract'].search(
            [('employee_id', '=', self.employee_id.id), ('state', '!=', 'cancel')], order='date_start asc', limit=1)
        self.first_contract = self.oldest_contract_id.date_start

    @api.onchange('notice_duration_month_before_2014', 'notice_duration_week_after_2014', 'start_notice_period', 'notice_respect')
    def _onchange_notice_duration(self):
        if self.notice_respect == 'without':
            self.end_notice_period = self.start_notice_period
        elif self.start_notice_period:
            months_to_weeks = self.notice_duration_month_before_2014 / 3.0 * 13
            self.end_notice_period = self.start_notice_period + timedelta(weeks=months_to_weeks+self.notice_duration_week_after_2014)

    @api.one
    @api.depends('first_contract', 'leaving_type', 'salary_december_2013', 'start_notice_period')
    def _notice_duration(self):
        first_2014 = datetime(2014, 1, 1)
        first_day_since_2014 = self.first_contract if self._get_years(relativedelta(first_2014, self.first_contract)) < 0 else first_2014
        period_since_2014 = relativedelta(self.start_notice_period, first_day_since_2014)
        difference_in_years = self._get_years(relativedelta(datetime(2013, 12, 31), self.first_contract))
        if self.leaving_type == 'fired':
            # Part I
            if difference_in_years > 0:
                self.salary_visibility = True
                if self.salary_december_2013 == 'inferior':
                    self.notice_duration_month_before_2014 = int(math.ceil(difference_in_years/5.0)*3.0)
                else:
                    self.notice_duration_month_before_2014 = max(int(math.ceil(difference_in_years)), 3)
            else:
                self.salary_visibility = False
                self.notice_duration_month_before_2014 = 0
            # Part II
            self.notice_duration_week_after_2014 = self._find_week(period_since_2014.months + period_since_2014.years*12, 'fired')
        elif self.leaving_type == 'resigned':
            self.salary_visibility = False
            if difference_in_years > 0:
                self.notice_duration_month_before_2014 = 3
                self.notice_duration_week_after_2014 = 0
            else:
                self.notice_duration_month_before_2014 = 0
                self.notice_duration_week_after_2014 = self._find_week(period_since_2014.months + period_since_2014.years*12, 'resigned')
        elif self.leaving_type == 'retired':
            self.salary_visibility = False
            self.notice_duration_month_before_2014 = 0
            self.notice_duration_week_after_2014 = 0

    def _get_years(self, date):
        return date.years + date.months/12 + date.days/365

    def _find_week(self, duration_worked_month, leaving_type):
        if leaving_type == 'resigned':
            duration_notice = [(3, 1), (6, 2), (9, 3), (12, 4), (18, 5), (24, 6), (36, 7), (48, 8),
                (60, 9), (72, 10), (84, 11), (96, 12), (108, 13)]
        else:
            duration_notice = [(3, 1), (4, 3), (5, 4), (6, 5), (9, 6), (12, 7), (15, 8), (18, 9),
                (21, 10), (24, 11), (36, 12), (48, 13), (60, 15), (72, 18), (84, 21), (96, 24),
                (108, 27), (120, 30), (132, 33), (144, 36), (156, 39), (168, 42), (180, 45), (192, 48),
                (204, 51), (216, 54), (228, 57), (240, 60), (252, 62), (264, 63), (276, 64), (288, 65)]
        for duration in duration_notice:
            last_valid = duration[1]
            if duration[0] > duration_worked_month:
                return last_valid
        return last_valid

    def validate_termination(self):
        self.employee_id.departure_reason = self.leaving_type
        self.employee_id.start_notice_period = self.start_notice_period
        self.employee_id.end_notice_period = self.end_notice_period
        self.employee_id.first_contract_in_company = self.first_contract

    def _create_input(self, name, payslip_id, sequence, code, amount, contract_id):
        self.env['hr.payslip.input'].create({
            'name' : name,
            'payslip_id': payslip_id,
            'sequence': sequence,
            'code': code,
            'amount': amount,
            'contract_id': contract_id
        })

    def compute_termination_fee(self):
        self.validate_termination()
        struct_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_salary_structure_departure_termination')

        termination_payslip = self.env['hr.payslip'].create({
            'name': '%s - %s' % (struct_id.payslip_name, self.employee_id.display_name),
            'employee_id': self.employee_id.id,
            'date_from': self.start_notice_period,
            'date_to': self.start_notice_period,
        })
        termination_payslip.onchange_employee()
        termination_payslip.struct_id = struct_id.id
        termination_payslip.worked_days_line_ids = ''

        contract_id = termination_payslip.contract_id.id
        payslip_id = termination_payslip.id

        self._create_input('Duration in month', payslip_id, 1, 'MONTHS', self.notice_duration_month_before_2014, contract_id)
        self._create_input('Duration in week', payslip_id, 2, 'WEEKS', self.notice_duration_week_after_2014, contract_id)
        self._create_input('Duration in calendar day', payslip_id, 3, 'DAYS', 0, contract_id)
        self._create_input('Unreasonable dismissal', payslip_id, 4, 'UNREASONABLE_DISMISSAL', 0, contract_id)
        self._create_input('Non respect motivation (= 2 weeks)', payslip_id, 5, 'NON_RESPECT_MOTIVATION', 0, contract_id)
        self._create_input('Year-end bonus', payslip_id, 10, 'YEAREND_BONUS', 0, contract_id)
        self._create_input('Home/Residence Allowance', payslip_id, 11, 'RESIDENCE', 0, contract_id)
        self._create_input('Expatrie Allowance', payslip_id, 12, 'EXPATRIE', 0, contract_id)
        self._create_input('Annual variable salary', payslip_id, 13, 'VARIABLE_SALARY', 0, contract_id)
        self._create_input('Monthly benefit in kind', payslip_id, 14, 'BENEFIT_IN_KIND', 0, contract_id)
        self._create_input('Monthly hospital insurance (employer\'s share)', payslip_id, 15, 'HOSPITAL_INSURANCE', 0, contract_id)
        self._create_input('Monthly group insurance (employer\'s share)', payslip_id, 16, 'GROUPE_INSURANCE', 0, contract_id)
        self._create_input('Stock Option', payslip_id, 17, 'STOCK_OPTION', 0, contract_id)
        self._create_input('Rules specific to Auxiliary Joint Committee', payslip_id, 18, 'SPECIFIC_RULES', 0, contract_id)
        self._create_input('Other monthly/yearly', payslip_id, 19, 'OTHER', 0, contract_id)

        return {
                'name': _('Termination'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hr.payslip',
                'type': 'ir.actions.act_window',
                'res_id': termination_payslip.id,
            }
