# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import math
import base64



class HrPayslipEmployeeDepartureTermination(models.TransientModel):
    _name = 'hr.payslip.employee.depature.termination'
    _description = 'Manage the Employee Departure Termination Fees'

    def _current_contract_id(self):
        return self.env['hr.contract'].search([('employee_id', '=', self.env.context.get('active_id')), ('state', '!=', 'cancel')], order='date_start desc', limit=1)

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id'))
    current_contract_id = fields.Many2one('hr.contract', string='Current Contract', default=_current_contract_id)

    wage = fields.Float('Gross Monthly Salary')
    wage_sum = fields.Float('Gross Monthly Salary', compute='_compute_wage_sum')
    home_allowance = fields.Float('Home/Residence Allowance')
    home_allowance_sum = fields.Float('Home/Residence Allowance', compute='_compute_home_allowance_sum')
    expat_allowance = fields.Float('Expatrie Allowance')
    expat_allowance_sum = fields.Float('Expatrie Allowance', compute='_compute_expat_allowance_sum')
    meal_vouchers = fields.Float('Meal Voucher Value')
    meal_vouchers_sum = fields.Float('Meal Voucher Value', compute='_compute_meal_vouchers_sum')
    eco_voucher = fields.Float('Eco Vouchers')
    variable_salary = fields.Float('Annual variable salary')
    pay_variable_sum = fields.Float('Pay on variable (15.34 of the annual amount)', compute='_compute_pay_variable_sum')
    # pay_variable = fields.Float('Pay on variable (15.34 of the annual amount)')
    benefit_in_kind = fields.Float('Monthly benefit in kind')
    benefit_in_kind_sum = fields.Float('Monthly benefit in kind', compute='_compute_benefit_in_kind_sum')
    benefit_any_kind = fields.Float('Advantage of any kind monthly')
    benefit_any_kind_sum = fields.Float('Advantage of any kind monthly', compute='_compute_benefit_any_kind_sum')
    car = fields.Float('Company Car')
    car_sum = fields.Float('Company Car', compute='_compute_car_sum')
    hospital_insurance = fields.Float('Monthly hospital insurance (employer\'s share)')
    hospital_insurance_sum = fields.Float('Monthly hospital insurance (employer\'s share)', compute='_compute_hospital_insurance_sum')
    group_insurance = fields.Float('Monthly group insurance (employer\'s share)')
    group_insurance_sum = fields.Float('Monthly group insurance (employer\'s share)', compute='_compute_group_insurance_sum')
    stock_option = fields.Float('Stock Option')
    stock_option_sum = fields.Float('Stock Option', compute='_compute_stock_option_sum')
    other = fields.Float('Other monthly/yearly')
    other_sum = fields.Float('Other monthly/yearly', compute='_compute_other_sum')

    salary_revalued = fields.Float('Annual salary revalued', compute='_compute_salary_revalued')
    notice_months = fields.Integer('Notice months', default=lambda self: self.env.context.get('notice_month'))
    salary_revalued_months = fields.Float('Salary for months', compute='_compute_salary_revalued_months')
    notice_weeks = fields.Integer('Notice weeks', default=lambda self: self.env.context.get('notice_week'))
    salary_revalued_weeks = fields.Float('Salary for weeks', compute='_compute_salary_revalued_weeks')
    notice_days = fields.Integer('Notice days')
    salary_revalued_days = fields.Float('Salary for days', compute='_compute_salary_revalued_days')
    total = fields.Float('Total', compute='_compute_total')

    @api.one
    @api.depends('employee_id')
    def _compute_current_contract_id(self):
        """ get the current contract """
        self.current_contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state', '!=', 'cancel')], order='date_start desc', limit=1)

    @api.one
    @api.depends('wage')
    def _compute_wage_sum(self):
        self.wage_sum = 12.92 * self.wage

    @api.one
    @api.depends('home_allowance')
    def _compute_home_allowance_sum(self):
        self.home_allowance_sum = 13.92 * self.home_allowance

    @api.one
    @api.depends('expat_allowance')
    def _compute_expat_allowance_sum(self):
        self.expat_allowance_sum = 12 * self.expat_allowance

    @api.one
    @api.depends('meal_vouchers')
    def _compute_meal_vouchers_sum(self):
        self.meal_vouchers_sum = 231 * self.meal_vouchers

    @api.one
    @api.depends('variable_salary')
    def _compute_pay_variable_sum(self):
        self.pay_variable_sum = 0.1534 * self.variable_salary

    @api.one
    @api.depends('benefit_in_kind')
    def _compute_benefit_in_kind_sum(self):
        self.benefit_in_kind_sum = 12.92 * self.benefit_in_kind

    @api.one
    @api.depends('benefit_any_kind')
    def _compute_benefit_any_kind_sum(self):
        self.benefit_any_kind_sum = 12.92 * self.benefit_any_kind

    @api.one
    @api.depends('car')
    def _compute_car_sum(self):
        self.car_sum = 12 * self.car

    @api.one
    @api.depends('hospital_insurance')
    def _compute_hospital_insurance_sum(self):
        self.hospital_insurance_sum = 12 * self.hospital_insurance

    @api.one
    @api.depends('group_insurance')
    def _compute_group_insurance_sum(self):
        self.group_insurance_sum = 12 * self.group_insurance

    @api.one
    @api.depends('stock_option')
    def _compute_stock_option_sum(self):
        self.stock_option_sum = 12 * self.stock_option

    @api.one
    @api.depends('other')
    def _compute_other_sum(self):
        self.other_sum = 12 * self.other

    @api.one
    @api.depends('wage_sum', 'home_allowance_sum', 'expat_allowance_sum', 'meal_vouchers_sum', 'eco_voucher', 'variable_salary', 'benefit_in_kind_sum', 'benefit_any_kind_sum', 'car_sum', 'hospital_insurance_sum', 'group_insurance_sum', 'stock_option_sum', 'other_sum')
    def _compute_salary_revalued(self):
        self.salary_revalued = self.wage_sum + self.home_allowance_sum + self.expat_allowance_sum\
            + self.meal_vouchers_sum + self.eco_voucher + self.variable_salary + self.pay_variable_sum\
            + self.benefit_any_kind_sum + self.benefit_in_kind_sum + self.car_sum + self.hospital_insurance_sum\
            + self.group_insurance_sum + self.stock_option_sum + self.other_sum

    @api.one
    @api.depends('salary_revalued', 'notice_months')
    def _compute_salary_revalued_months(self):
        self.salary_revalued_months = self.notice_months * self.salary_revalued / 12.0

    @api.one
    @api.depends('salary_revalued', 'notice_weeks')
    def _compute_salary_revalued_weeks(self):
        self.salary_revalued_weeks = self.notice_weeks * self.salary_revalued * 3.0 / (12.0 * 13.0)

    @api.one
    @api.depends('salary_revalued', 'notice_days')
    def _compute_salary_revalued_days(self):
        self.salary_revalued_days = self.notice_days * self.salary_revalued * 3.0 / (12.0 * 13.0 * 5.0)

    @api.one
    @api.depends('salary_revalued_months', 'salary_revalued_weeks', 'salary_revalued_days')
    def _compute_total(self):
        self.total = self.salary_revalued_months + self.salary_revalued_weeks + self.salary_revalued_days

    @api.onchange('current_contract_id')
    def _onchange_contract(self):
        self.wage = self.current_contract_id.wage
        self.meal_vouchers = self.current_contract_id.meal_voucher_amount
        self.eco_voucher = self.current_contract_id.eco_checks
        self.benefit_in_kind = self.current_contract_id.internet + self.current_contract_id.mobile + self.current_contract_id.mobile_plus
        self.other = self.current_contract_id.additional_net_amount
    
    def print_report(self):
        # data = {}
        # # return self.env['ir.actions.report'].get_action(self, 'l10n_be_hr_payroll.termination_fees', data=data)
        # # # report = self.env['ir.actions.report']._get_report_from_name('l10n_be_hr_payroll.termination_fees')
        # # # return {
        # # #     'report_type': data.get('report_type') if data else '',
        # # # }
        # report_name = 'l10n_be_hr_payroll.termination_fees'
        # active_ids = self.env.get('active_ids')
        # active_model = self.env.get('active_model')
        # docids = active_ids #self.env[active_model].browse(active_ids)
        # return (self.env['ir.actions.report'].search([('report_name', '=', report_name)], limit=1)
        #                 .with_context(data)
        #                 .report_action(docids))
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'wage': self.wage,
                'meal_vouchers': self.meal_vouchers,
            },
            'wage': self.wage,
            'wage_sum': self.wage_sum,
            'home_allowance': self.home_allowance,
            'home_allowance_sum': self.home_allowance_sum,
            'expat_allowance': self.expat_allowance,
            'expat_allowance_sum': self.expat_allowance_sum,
            'meal_vouchers': self.meal_vouchers,
            'meal_vouchers_sum': self.meal_vouchers_sum,
            'eco_voucher': self.eco_voucher,
            'variable_salary': self.variable_salary,
            'pay_variable_sum': self.pay_variable_sum,
            'benefit_in_kind': self.benefit_in_kind,
            'benefit_in_kind_sum': self.benefit_in_kind_sum,
            'benefit_any_kind': self.benefit_any_kind,
            'benefit_any_kind_sum': self.benefit_any_kind_sum,
            'car': self.car,
            'car_sum': self.car_sum,
            'hospital_insurance': self.hospital_insurance,
            'hospital_insurance_sum': self.hospital_insurance_sum,
            'group_insurance': self.group_insurance,
            'group_insurance_sum': self.group_insurance_sum,
            'stock_option': self.stock_option,
            'stock_option_sum': self.stock_option_sum,
            'other': self.other,
            'other_sum': self.other_sum,
            'salary_revalued': self.salary_revalued,
            'notice_months': self.notice_months,
            'salary_revalued_months': self.salary_revalued_months,
            'notice_weeks': self.notice_weeks,
            'salary_revalued_weeks': self.salary_revalued_weeks,
            'notice_days': self.notice_days,
            'salary_revalued_days': self.salary_revalued_days,
            'total': self.total,
        }

        # use `module_name.report_id` as reference.
        # `report_action()` will call `get_report_values()` and pass `data` automatically.
        # return self.env.ref('l10n_be_hr_payroll.termination_fees').report_action(self)
        # return self.env.ref('l10n_be_hr_payroll.termination_fees').report_action(self, data=data)
        # datas = {'ids': self.env.context.get('active_ids', [])}
       
        result, format = self.env.ref('l10n_be_hr_payroll.termination_fees').render_qweb_pdf(self.employee_id.id, data=data)
        display_name = _("Termination Fees - %s") % self.employee_id.display_name
        attachment = self.env['ir.attachment'].create({
            'name': display_name,
            'datas': base64.b64encode(result),
            'datas_fname': display_name + '.pdf',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'type': 'binary',
        })
        # return attachment.action_get()
        # return (self.env.ref('l10n_be_hr_payroll.termination_fees').with_context(groups='hr.group_hr_manager', attachment='123').report_action([], data=data))
        # return result
        # return self.env.ref('l10n_be_hr_payroll.termination_fees').with_context(groups='hr.group_hr_manager', attachment='123').report_action([], data=datas)

class HrPayrollDepartureReferenceReport(models.AbstractModel):
    _name = 'report.l10n_be_hr_payroll.termination_fees'

    @api.model
    def _get_report_values(self, docids, data=None):
        print(data)
        print('sdfgsdfgsdfgsqflgksqdgfkjhsqwkduyhfgqkdusjfgk')
        report = self.env['ir.actions.report']._get_report_from_name('l10n_be_hr_payroll.termination_fees')
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'docs': self.env[report.model].browse(docids),
            'data': data,
        }
        # docargs = {
        #    'doc_ids': self.ids,
        #    'doc_model': self.model,
        #    'data': data,
        # }
        # return self.env['ir.actions.report'].render('l10n_be_hr_payroll.termination_fees', docargs)

