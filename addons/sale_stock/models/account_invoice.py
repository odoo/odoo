# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    incoterms_id = fields.Many2one('stock.incoterms', string="Incoterms",
        help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.",
        readonly=True, states={'draft': [('readonly', False)]})


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        price_unit = super(AccountInvoiceLine,self)._get_anglo_saxon_price_unit()
        # in case of anglo saxon with a product configured as invoiced based on delivery, with perpetual
        # valuation and real price costing method, we must find the real price for the cost of good sold
        if self.product_id.invoice_policy == "delivery":
            for s_line in self.sale_line_ids:
                # qtys already invoiced
                qty_done = sum([x.uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.invoice_id.state in ('open', 'paid')])
                quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = s_line.mapped('procurement_ids.move_ids').sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                average_price_unit = self._compute_average_price(qty_done, quantity, moves)
                price_unit = average_price_unit or price_unit
                price_unit = self.product_id.uom_id._compute_price(price_unit, self.uom_id)
        return price_unit

    def _compute_average_price(self, qty_done, quantity, moves):
        average_price_unit = 0
        qty_delivered = 0
        invoiced_qty = 0
        for move in moves:
            if move.state != 'done':
                continue
            invoiced_qty += move.product_qty
            if invoiced_qty <= qty_done:
                continue
            qty_to_consider = move.product_qty
            if invoiced_qty - move.product_qty < qty_done:
                qty_to_consider = invoiced_qty - qty_done
            qty_to_consider = min(qty_to_consider, quantity - qty_delivered)
            qty_delivered += qty_to_consider
            if qty_delivered:
                average_price_unit = (average_price_unit * (qty_delivered - qty_to_consider) + move.price_unit * qty_to_consider) / qty_delivered
            if qty_delivered == quantity:
                break
        return average_price_unit
