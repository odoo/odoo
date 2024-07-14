# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nBeDecemberSlipWizard(models.TransientModel):
    _name = 'l10n.be.december.slip.wizard'
    _description = 'CP200: December Slip Computation'

    @api.model
    def default_get(self, fields_list):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        result = super(L10nBeDecemberSlipWizard, self).default_get(fields_list)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'hr.payslip':
            payslip_id = self.env.context['active_id']
            result['payslip_id'] = payslip_id
        return result

    payslip_id = fields.Many2one('hr.payslip')
    employee_id = fields.Many2one('hr.employee', related="payslip_id.employee_id")
    contract_id = fields.Many2one('hr.contract', related="payslip_id.contract_id")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id")
    remuneration_n1 = fields.Monetary(
        string="Remuneration N-1",
        compute='_compute_remuneration_n1', store=True, readonly=False)
    simple_holiday_n1 = fields.Monetary(
        string="Simple Holiday Pay N-1",
        compute='_compute_holiday_pay_n1', store=True, readonly=False)
    double_holiday_n1 = fields.Monetary(
        string="Double Holiday Pay N-1",
        compute='_compute_holiday_pay_n1', store=True, readonly=False)
    simple_holiday_n = fields.Monetary(
        string="Simple Holiday Pay N",
        compute='_compute_holiday_pay_n', store=True, readonly=False)
    double_holiday_n = fields.Monetary(
        string="Double Holiday Pay N",
        compute='_compute_holiday_pay_n', store=True, readonly=False)
    simple_december_pay = fields.Monetary(
        string="Simple December Pay",
        compute='_compute_simple_december_pay', store=True, readonly=False)
    double_december_pay = fields.Monetary(
        string="Double December Pay",
        compute='_compute_double_december_pay', store=True, readonly=False)

    @api.depends('simple_holiday_n', 'simple_holiday_n1')
    def _compute_simple_december_pay(self):
        for wizard in self:
            wizard.simple_december_pay = max(0, wizard.simple_holiday_n1 - wizard.simple_holiday_n)

    @api.depends('double_holiday_n', 'double_holiday_n1')
    def _compute_double_december_pay(self):
        for wizard in self:
            wizard.double_december_pay = max(0, wizard.double_holiday_n1 - wizard.double_holiday_n)

    @api.depends('employee_id')
    def _compute_remuneration_n1(self):
        for wizard in self:
            current_year = wizard.payslip_id.date_from.replace(month=1, day=1)
            previous_year = current_year + relativedelta(years=-1)
            monthly_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary')

            payslips_n1 = self.env['hr.payslip'].search([
                ('employee_id', '=', wizard.employee_id.id),
                ('date_to', '>=', previous_year),
                ('date_from', '<', current_year),
                ('state', 'in', ['done', 'paid']),
                ('struct_id', '=', monthly_pay.id)])
            wizard.remuneration_n1 = payslips_n1._origin._get_line_values(
                ['SALARY'], compute_sum=True)['SALARY']['sum']['total']

    @api.depends('remuneration_n1')
    def _compute_holiday_pay_n1(self):
        for wizard in self:
            amount = wizard.remuneration_n1 * 0.0767
            wizard.simple_holiday_n1 = amount
            wizard.double_holiday_n1 = amount

    @api.depends('employee_id')
    def _compute_holiday_pay_n(self):
        for wizard in self:
            current_year = wizard.payslip_id.date_from.replace(month=1, day=1)
            monthly_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary')
            double_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday')

            payslips_n = self.env['hr.payslip'].search([
                ('employee_id', '=', wizard.employee_id.id),
                ('date_to', '>=', current_year),
                ('state', 'in', ['done', 'paid', 'verify']),
                ('struct_id', 'in', (monthly_pay + double_pay).ids)])
            double_payslip = payslips_n.filtered(lambda p: p.struct_id == double_pay)
            payslips_n -= double_payslip
            wizard.double_holiday_n = double_payslip._origin._get_line_values(
                ['BASIC'], compute_sum=True)['BASIC']['sum']['total']
            wizard.simple_holiday_n = payslips_n._get_worked_days_line_amount('LEAVE120')

    def action_validate(self):
        self.ensure_one()
        input_line_vals = []

        simple_input = self.env.ref('l10n_be_hr_payroll.input_simple_december_pay')
        lines_to_remove = self.payslip_id.input_line_ids.filtered(
            lambda x: x.input_type_id == simple_input)
        to_remove_vals = [(3, line.id, False) for line in lines_to_remove]
        to_add_vals = [(0, 0, {
            'amount': self.simple_december_pay,
            'input_type_id': simple_input.id
        })]
        input_line_vals += to_remove_vals + to_add_vals

        double_input = self.env.ref('l10n_be_hr_payroll.input_double_december_pay')
        lines_to_remove = self.payslip_id.input_line_ids.filtered(
            lambda x: x.input_type_id == double_input)
        to_remove_vals = [(3, line.id, False) for line in lines_to_remove]
        to_add_vals = [(0, 0, {
            'amount': self.double_december_pay,
            'input_type_id': double_input.id
        })]
        input_line_vals += to_remove_vals + to_add_vals

        self.payslip_id.update({'input_line_ids': input_line_vals})
