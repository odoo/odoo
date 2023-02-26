# -*- coding: utf-8 -*-
import time
from odoo import models, api, fields,tools
from odoo.exceptions import UserError
from datetime import date, datetime, time
import babel
from datetime import date, datetime, time



class HrLoanAcc(models.Model):
    _inherit = 'hr.loan'

    employee_account_id = fields.Many2one('account.account', string="Loan Account")
    treasury_account_id = fields.Many2one('account.account', string="Treasury Account")
    journal_id = fields.Many2one('account.journal', string="Journal")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('waiting_approval_2', 'Waiting Approval'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    def action_approve(self):
        """This create account move for request.
            """
        loan_approve = self.env['ir.config_parameter'].sudo().get_param('account.loan_approve')
        contract_obj = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
        if not contract_obj:
            raise UserError('You must Define a contract for employee')
        if not self.loan_lines:
            raise UserError('You must compute installment before Approved')
        if loan_approve:
            self.write({'state': 'waiting_approval_2'})
        else:
            if not self.employee_account_id or not self.treasury_account_id or not self.journal_id:
                raise UserError("You must enter employee account & Treasury account and journal to approve ")
            if not self.loan_lines:
                raise UserError('You must compute Loan Request before Approved')
            timenow = date.today()
            for loan in self:
                amount = loan.loan_amount
                loan_name = loan.employee_id.name
                reference = loan.name
                journal_id = loan.journal_id.id
                debit_account_id = loan.treasury_account_id.id
                credit_account_id = loan.employee_account_id.id
                debit_vals = {
                    'name': loan_name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'loan_id': loan.id,
                }
                credit_vals = {
                    'name': loan_name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'loan_id': loan.id,
                }
                print("22222",debit_vals)
                print("8888",credit_vals)
                vals = {
                    'name': 'Loan For' + ' ' + loan_name,
                    'narration': loan_name,
                    'ref': reference,
                    'journal_id': journal_id,
                    'date': timenow,
                    'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                }
                move = self.env['account.move'].create(vals)
                print("0000", move)
                move.action_post()
            self.write({'state': 'approve'})
        return True

    def action_double_approve(self):
        """This create account move for request in case of double approval.
            """
        if not self.employee_account_id or not self.treasury_account_id or not self.journal_id:
            raise UserError("You must enter employee account & Treasury account and journal to approve ")
        if not self.loan_lines:
            raise UserError('You must compute Loan Request before Approved')
        timenow = date.today()
        for loan in self:
            amount = loan.loan_amount
            loan_name = loan.employee_id.name
            reference = loan.name
            journal_id = loan.journal_id.id
            debit_account_id = loan.treasury_account_id.id
            credit_account_id = loan.employee_account_id.id
            debit_vals = {
                'name': loan_name,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'loan_id': loan.id,
            }
            credit_vals = {
                'name': loan_name,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'loan_id': loan.id,
            }
            vals = {
                'name': 'Loan For' + ' ' + loan_name,
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': timenow,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move = self.env['account.move'].create(vals)
            move.action_post()()
        self.write({'state': 'approve'})

        return True


class HrLoanLineAcc(models.Model):
    _inherit = "hr.loan.line"

    def action_paid_amount(self,month):
        """This create the account move line for payment of each installment.
            """
        timenow = date.today()

        for line in self:
            if line.loan_id.state != 'approve':
                raise UserError("Loan Request must be approved")
            amount = line.amount
            loan_name = line.employee_id.name
            reference = line.loan_id.name
            journal_id = line.loan_id.journal_id.id
            debit_account_id = line.loan_id.employee_account_id.id
            credit_account_id = line.loan_id.treasury_account_id.id
            name = 'LOAN/' + ' ' + loan_name + '/' + month
            debit_vals = {
                'name': loan_name,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
            }
            credit_vals = {
                'name': loan_name,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
            }

            vals = {
                'name': name,
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': timenow,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }

            move = self.env['account.move'].create(vals)
            move.action_post()()
        return True


class HrPayslipAcc(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        for line in self.input_line_ids:
            date_from = self.date_from
            tym = datetime.combine(fields.Date.from_string(date_from), time.min)
            locale = self.env.context.get('lang') or 'en_US'
            month = tools.ustr(babel.dates.format_date(date=tym, format='MMMM-y', locale=locale))
            if line.loan_line_id:
                line.loan_line_id.action_paid_amount(month)
        return super(HrPayslipAcc, self).action_payslip_done()
