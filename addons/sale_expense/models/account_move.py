# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _sale_determine_order(self):
        """ For move lines created from expense, we override the normal behavior.
            Note: if no SO but an AA is given on the expense, we will determine anyway the SO from the AA, using the same
            mecanism as in Vendor Bills.
        """
        mapping_from_invoice = super(AccountMoveLine, self)._sale_determine_order()

        mapping_from_expense = {}
        for move_line in self.filtered(lambda move_line: move_line.expense_id):
            if move_line.expense_id.sale_order_id:
                mapping_from_expense[move_line.id] = move_line.expense_id.sale_order_id or None

        mapping_from_invoice.update(mapping_from_expense)
        return mapping_from_invoice
