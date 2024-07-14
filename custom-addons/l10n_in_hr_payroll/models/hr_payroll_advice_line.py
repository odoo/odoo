# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayrollAdviceLine(models.Model):
    _name = 'hr.payroll.advice.line'
    _description = 'Bank Advice Lines'

    advice_id = fields.Many2one('hr.payroll.advice', string='Bank Advice')
    name = fields.Char('Bank Account No.', required=True)
    ifsc_code = fields.Char(string='IFSC Code')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    bysal = fields.Float(string='By Salary', digits='Payroll')
    debit_credit = fields.Char(string='C/D', default='C')
    company_id = fields.Many2one('res.company', related='advice_id.company_id', string='Company', store=True, readonly=False)
    ifsc = fields.Boolean(related='advice_id.neft', string='IFSC', readonly=False)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.name = self.employee_id.bank_account_id.acc_number
        self.ifsc_code = self.employee_id.bank_account_id.bank_bic or ''
