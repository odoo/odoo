# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from datetime import datetime, timedelta
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

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id'))
    leaving_type_id = fields.Many2one('hr.departure.reason', string='Departure Reason', required=True)
    departure_reason_code = fields.Integer(related='leaving_type_id.reason_code')

    start_notice_period = fields.Date('Start notice period', required=True, default=fields.Date.context_today)
    end_notice_period = fields.Date('End notice period', required=True)
    departure_description = fields.Char('Departure Description', required=True)
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
        ('with', 'Employee works during his notice period'),
        ('without', "Employee doesn't work during his notice period")
        ], string='Respect of the notice period', required=True, default='with',
        help='Decides whether the employee will still work during his notice period or not.')

    @api.depends('employee_id')
    def _compute_oldest_contract_id(self):
        """ get the oldest contract """
        for notice in self:
            notice.oldest_contract_id = self.env['hr.contract'].search([
                ('employee_id', '=', notice.employee_id.id),
                ('state', '!=', 'cancel')
            ], order='date_start asc', limit=1)
            notice.first_contract = notice.oldest_contract_id.date_start

    @api.onchange('notice_duration_month_before_2014', 'notice_duration_week_after_2014', 'start_notice_period', 'notice_respect')
    def _onchange_notice_duration(self):
        if self.notice_respect == 'without':
            self.end_notice_period = self.start_notice_period
        elif self.start_notice_period:
            months_to_weeks = self.notice_duration_month_before_2014 / 3.0 * 13
            self.end_notice_period = self.start_notice_period + timedelta(weeks=months_to_weeks+self.notice_duration_week_after_2014)

    @api.depends('first_contract', 'leaving_type_id', 'salary_december_2013', 'start_notice_period')
    def _notice_duration(self):
        first_2014 = datetime(2014, 1, 1)
        departure_reasons = self.env['hr.departure.reason']._get_default_departure_reasons()
        for notice in self:
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
                        notice.notice_duration_month_before_2014 = int(math.ceil(difference_in_years/5.0)*3.0)
                    else:
                        notice.notice_duration_month_before_2014 = max(int(math.ceil(difference_in_years)), 3)
                else:
                    notice.salary_visibility = False
                    notice.notice_duration_month_before_2014 = 0
                # Part II
                notice.notice_duration_week_after_2014 = notice._find_week(
                    period_since_2014.months + period_since_2014.years*12, 'fired')
            elif notice.leaving_type_id.reason_code == departure_reasons['resigned']:
                notice.salary_visibility = False
                notice.notice_duration_month_before_2014 = 0
                notice.notice_duration_week_after_2014 = notice._find_week(
                    period_since_2014.months + period_since_2014.years*12, 'resigned')
            elif notice.leaving_type_id.reason_code == departure_reasons['retired']:
                notice.salary_visibility = False
                notice.notice_duration_month_before_2014 = 0
                notice.notice_duration_week_after_2014 = 0
            else:
                notice.salary_visibility = False
                notice.notice_duration_month_before_2014 = 0
                notice.notice_duration_week_after_2014 = 0

    def _get_years(self, date):
        return date.years + date.months/12 + date.days/365

    def _find_week(self, duration_worked_month, leaving_type_id):
        if leaving_type_id == 'resigned':
            duration_notice = [
                (3, 1), (6, 2), (12, 3), (18, 4), (24, 5), (48, 6), (60, 7), (72, 9),
                (84, 10), (96, 12), (1000, 13)]
        else:
            duration_notice = [
                (3, 1), (4, 3), (5, 4), (6, 5), (9, 6), (12, 7), (15, 8), (18, 9),
                (21, 10), (24, 11), (36, 12), (48, 13), (60, 15), (72, 18), (84, 21), (96, 24),
                (108, 27), (120, 30), (132, 33), (144, 36), (156, 39), (168, 42), (180, 45), (192, 48),
                (204, 51), (216, 54), (228, 57), (240, 60), (252, 62), (264, 63), (276, 64), (288, 65)]
        for duration in duration_notice:
            last_valid = duration[1]
            if duration[0] > duration_worked_month:
                return last_valid
        return last_valid

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
            'name': '%s - %s' % (struct_id.payslip_name, self.employee_id.display_name),
            'employee_id': self.employee_id.id,
            'date_from': self.start_notice_period,
            'date_to': self.start_notice_period,
            'contract_id': last_contract.id,
            'struct_id': struct_id.id,
        })
        termination_payslip.worked_days_line_ids = [(5, 0, 0)]

        contract = termination_payslip.contract_id
        payslip_id = termination_payslip.id

        self._create_input(payslip_id, 1, 'months', self.notice_duration_month_before_2014, contract.id)
        self._create_input(payslip_id, 2, 'weeks', self.notice_duration_week_after_2014, contract.id)
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
