# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    qty_waiting_for_receipt = fields.Float(
        default=0, help="Quantity invoiced but not received yet.")

    def _update_qty_waiting_for_receipt(self):
        # TODO: Could be set directly in `_stock_account_prepare_anglo_saxon_in_lines_vals` ?
        for line in self:
            po_line = line.purchase_line_id
            line.qty_waiting_for_receipt = min(line.quantity, po_line.qty_invoiced - po_line.qty_received)
