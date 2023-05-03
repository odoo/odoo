# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_cancel(self):
        for l in self.line_ids:
            if l.expense_id:
                l.expense_id.refuse_expense(reason=_("Payment Cancelled"))
        return super().button_cancel()

    def button_draft(self):
        for line in self.line_ids:
            if line.expense_id:
                line.expense_id.sheet_id.write({'state': 'post'})
        return super().button_draft()
