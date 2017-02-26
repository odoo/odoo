# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def unlink(self):
        expense_sheets = self.env['hr.expense.sheet'].search([('account_move_id', 'in', self.ids)])
        res = super(AccountMove, self).unlink()
        if expense_sheets:
            expense_sheets.write({'state': 'approve'})
        return res
