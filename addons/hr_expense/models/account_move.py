# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_sheet_id = fields.One2many('hr.expense.sheet', 'account_move_id')

    def action_open_expense_report(self):
        self.ensure_one()
        return {
            'name': self.expense_sheet_id.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'res_id': self.expense_sheet_id.id
        }

    def _payment_state_matters(self):
        self.ensure_one()
        if self.line_ids.expense_id:
            return True
        return super()._payment_state_matters()

    def button_cancel(self):
        super(AccountMove, self).button_cancel()
        self.line_ids.expense_id.refuse_expense(_('Payment Refused'))
