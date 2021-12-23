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

    def _create_payments(self):
        # OVERRIDE to set the 'done' state on expense sheets.
        payments = super()._create_payments()

        expense_sheets = self.env['hr.expense.sheet'].search([('account_move_id', 'in', self.line_ids.move_id.ids)])
        for expense_sheet in expense_sheets:
            if expense_sheet.currency_id.is_zero(expense_sheet.amount_residual):
                expense_sheet.state = 'done'

        return payments
