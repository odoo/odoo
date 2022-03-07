# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_line_batch_key(self, line):
        # OVERRIDE to set the bank account defined on the employee
        res = super()._get_line_batch_key(line)
        expense_sheet = self.env['hr.expense.sheet'].search([('payment_mode', '=', 'own_account'), ('account_move_id', 'in', line.move_id.ids)])
        if expense_sheet and not line.move_id.partner_bank_id:
            res['partner_bank_id'] = expense_sheet.employee_id.bank_account_id.id or line.partner_id.bank_ids and line.partner_id.bank_ids.ids[0]
        return res

    def _init_payments(self, to_process, edit_mode=False):
        # OVERRIDE
        payments = super()._init_payments(to_process, edit_mode=edit_mode)
        for payment, vals in zip(payments, to_process):
            expenses = vals['batch']['lines'].expense_id
            if expenses:
                payment.line_ids.write({'expense_id': expenses[0].id})
        return payments

    def _reconcile_payments(self, to_process, edit_mode=False):
        # OVERRIDE
        res = super()._reconcile_payments(to_process, edit_mode=edit_mode)
        for vals in to_process:
            expense_sheets = vals['batch']['lines'].expense_id.sheet_id
            for expense_sheet in expense_sheets:
                if expense_sheet.currency_id.is_zero(expense_sheet.amount_residual):
                    expense_sheet.state = 'done'
        return res
