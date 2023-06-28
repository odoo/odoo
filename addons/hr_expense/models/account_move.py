# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_cancel(self):
        """Get all expenses for refuse"""
        expense_lines = self.line_ids.mapped("expense_id.sheet_id").mapped("expense_line_ids")
        for exp in expense_lines:
            exp.refuse_expense(reason=_("Payment Cancelled"))
        return super().button_cancel()

    def button_draft(self):
        for line in self.line_ids:
            if line.expense_id:
                line.expense_id.sheet_id.write({'state': 'post'})
        return super().button_draft()
