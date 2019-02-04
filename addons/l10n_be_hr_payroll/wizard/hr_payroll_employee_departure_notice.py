# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import math


class HrPayslipEmployeeDepartureNotice(models.TransientModel):
    _name = 'hr.payslip.employee.depature.notice'
    _description = 'Manage the Employee Departure Notice Duration'

    # status = fields.Selection([('nd', 'Notice Duration'), ('nd_with_salary', 'Notice Duration with Salary'), ('termination_fees', 'Termination Fees'), ('leave1', 'Leave 1'), ('leave2', 'Leave 2')], string='Leaving Type', required=True, default='nd')

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id'))
    leaving_type = fields.Selection([('dissmissed', 'Dissmissed'), ('quit', 'Quit')], string='Leaving Type', required=True, default='dissmissed')
    start_notice_period = fields.Date('Start notice period', default=fields.Date.context_today)
    end_notice_period = fields.Date('End notice period')

    contract_ids = fields.Many2many('hr.contract', string='Employee Contracts', compute='_compute_contract_ids')
    oldest_contract_id = fields.Many2one('hr.contract', string='Oldest Contract', compute='_compute_oldest_contract_id')
    first_contract = fields.Date('First contract in company')

    salary_december_2013 = fields.Selection([('inferior', 'Gross annual salary < 32.254 €'), ('superior', 'Gross annual salary > 32.254 €')], string='Gross Annual Salary as of December 31, 2013', required=True, default='superior')
    salary_visibility = fields.Boolean('Salary as of December 2013')
    notice_duration_month_before_2014 = fields.Integer('Notice Duration in month', compute='_notice_duration')
    notice_duration_week_after_2014 = fields.Integer('Notice Duration in weeks', compute='_notice_duration')

    notice_respect = fields.Selection([('with', 'Employee will leave after notice period'), ('without', 'Employee will leave before notice period')], string='Respect of the notice period', required=True, default='with')


    @api.one
    @api.depends('employee_id')
    def _compute_contract_ids(self):
        """ get all contract """
        # for contract in self:
        self.contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state', '!=', 'cancel')])

    @api.one
    @api.depends('employee_id')
    def _compute_oldest_contract_id(self):
        """ get the oldest contract """
        self.oldest_contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state', '!=', 'cancel')], order='date_start asc', limit=1)
        self.first_contract = self.oldest_contract_id.date_start

    @api.onchange('notice_duration_month_before_2014', 'notice_duration_week_after_2014', 'start_notice_period')
    def _onchange_notice_duration(self):
        months_to_weeks = self.notice_duration_month_before_2014 / 3.0 * 13
        self.end_notice_period = self.start_notice_period + timedelta(weeks=months_to_weeks+self.notice_duration_week_after_2014)


    @api.one
    @api.depends('first_contract', 'leaving_type', 'salary_december_2013', 'start_notice_period')
    def _notice_duration(self):
        first_2014 = datetime(2014, 1, 1)
        first_day_since_2014 = self.first_contract if self._get_years(relativedelta(first_2014, self.first_contract)) < 0 else first_2014
        period_since_2014 = relativedelta(self.start_notice_period, first_day_since_2014)
        difference_in_years = self._get_years(relativedelta(datetime(2013, 12, 31), self.first_contract))
        if self.leaving_type == 'dissmissed': #licencié
            # Part I
            if difference_in_years > 0:
                self.salary_visibility = True
                # self.status = 'nd_with_salary'
                if self.salary_december_2013 == 'inferior':
                    self.notice_duration_month_before_2014 = int(math.ceil(difference_in_years/5.0)*3.0)
                else:
                    self.notice_duration_month_before_2014 = max(int(math.ceil(difference_in_years)), 3)
            else:
                self.salary_visibility = False
                # self.status = 'nd'
                self.notice_duration_month_before_2014 = 0
            # Part II
            self.notice_duration_week_after_2014 = self._find_week(period_since_2014.months + period_since_2014.years*12, 'dissmissed')
        else:
            # self.status = 'nd'
            self.salary_visibility = False
            if difference_in_years > 0:
                self.notice_duration_month_before_2014 = 3
                self.notice_duration_week_after_2014 = 0
            else:
                self.notice_duration_month_before_2014 = 0
                self.notice_duration_week_after_2014 = self._find_week(period_since_2014.months + period_since_2014.years*12, 'quit')

    def _get_years(self, date):
        return date.years + date.months/12 + date.days/365

    def _find_week(self, duration_worked_month, leaving_type):
        if leaving_type == 'quit':
            duration_notice = [(3, 1), (6, 2), (9, 3), (12, 4), (18, 5), (24, 6), (36, 7), (48, 8), (60, 9), (72, 10), (84, 11), (96, 12), (1000, 13)]
        else:
            duration_notice = [(3, 1), (4, 3), (5, 4), (6, 5), (9, 6), (12, 7), (15, 8), (18, 9), (21, 10), (24, 11), (36, 12), (48, 13), (60, 15), (72, 18), (84, 21), (96, 24), (108, 27), (120, 30), (132, 33), (144, 36), (156, 39), (168, 42), (180, 45), (192, 48), (204, 51), (216, 54), (228, 57), (240, 60), (252, 62), (264, 63), (276, 64), (288, 65)]
        for duration in duration_notice:
            last_valid = duration[1]
            if duration[0] > duration_worked_month:
                return last_valid
        return last_valid

    def compute_termination_fee(self):
        return {
            'name': _('Employee Departure Termination Fees'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.employee.depature.termination',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.env.context.get('active_id'),
                'notice_month': self.notice_duration_month_before_2014,
                'notice_week': self.notice_duration_week_after_2014,
            }
        }
