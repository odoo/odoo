# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_batch_available_partner_banks(self, batch_result, journal):
        # OVERRIDE to set the bank account defined on the employee
        expense_sheet = batch_result['lines'].move_id.expense_sheet_id.filtered(lambda sheet: sheet and sheet.payment_mode == 'own_account')
        if expense_sheet and batch_result['payment_values']['payment_type'] == 'outbound':
            # We use sudo since we may not have access to the employee_id record. If the env wasn't already in sudo,
            # we should un-sudo the record before returning it.
            sudo_bank_account_id = expense_sheet.employee_id.sudo().bank_account_id
            return sudo_bank_account_id.sudo(self.env.su)
        else:
            return super()._get_batch_available_partner_banks(batch_result, journal)

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
