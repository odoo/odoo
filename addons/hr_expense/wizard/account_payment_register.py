# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payments(self):
        # OVERRIDE to set the 'done' state on expense sheets.
        payments = super()._create_payments()

        expense_sheets = self.env['hr.expense.sheet'].search([('account_move_id', 'in', self.line_ids.move_id.ids)])
        for expense_sheet in expense_sheets:
            if expense_sheet.currency_id.is_zero(expense_sheet.amount_residual):
                expense_sheet.state = 'done'

        return payments
