# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        price_unit = super(AccountInvoiceLine, self)._get_anglo_saxon_price_unit()
        if self.product_id._get_invoice_policy() == "delivery" and self.env.context.get("pos_picking_id"):
            moves = (
                self.env.context["pos_picking_id"]
                .move_lines.filtered(lambda m: m.product_id == self.product_id)
                .sorted(lambda x: x.date)
            )
            quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            average_price_unit = self.product_id._compute_average_price(0.0, quantity, moves)
            price_unit = average_price_unit or price_unit
            price_unit = self.product_id.uom_id._compute_price(price_unit, self.uom_id)

        return price_unit
