# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.type == 'out_invoice'):
            rslt += invoice.mapped('invoice_line_ids.sale_line_ids.order_id.picking_ids.move_lines').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
        for invoice in self.filtered(lambda x: x.type == 'out_refund'):
            rslt += invoice.mapped('reversed_entry_id.invoice_line_ids.sale_line_ids.order_id.picking_ids.move_lines').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return rslt

    def _get_invoiced_lot_values(self):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()

        if self.state == 'draft':
            return []

        sale_orders = self.mapped('invoice_line_ids.sale_line_ids.order_id')
        stock_move_lines = sale_orders.mapped('picking_ids.move_lines.move_line_ids')

        # Get the other customer invoices and refunds.
        ordered_invoice_ids = sale_orders.mapped('invoice_ids')\
            .filtered(lambda i: i.state != 'draft')\
            .sorted(lambda i: (i.date_invoice, i.id))

        # Get the position of self in other customer invoices and refunds.
        self_index = None
        i = 0
        for invoice in ordered_invoice_ids:
            if invoice.id == self.id:
                self_index = i
                break
            i += 1

        # Get the previous invoice if any.
        previous_invoices = ordered_invoice_ids[:self_index]
        last_invoice = previous_invoices[-1] if len(previous_invoices) else None

        # Get the incoming and outgoing sml between self.invoice_date and the previous invoice (if any).
        self_datetime = max(self.invoice_line_ids.mapped('write_date'))
        last_invoice_datetime = max(last_invoice.invoice_line_ids.mapped('write_date')) if last_invoice else None

        def _filter_incoming_sml(ml):
            if ml.state == 'done' and ml.location_id.usage == 'customer' and ml.lot_id:
                if last_invoice_datetime:
                    return last_invoice_datetime <= ml.date <= self_datetime
                else:
                    return ml.date <= self_datetime
            return False

        def _filter_outgoing_sml(ml):
            if ml.state == 'done' and ml.location_dest_id.usage == 'customer' and ml.lot_id:
                if last_invoice_datetime:
                    return last_invoice_datetime <= ml.date <= self_datetime
                else:
                    return ml.date <= self_datetime
            return False

        incoming_sml = stock_move_lines.filtered(_filter_incoming_sml)
        outgoing_sml = stock_move_lines.filtered(_filter_outgoing_sml)

        # Prepare and return lot_values
        qties_per_lot = defaultdict(lambda: 0)
        if self.type == 'out_refund':
            for ml in outgoing_sml:
                qties_per_lot[ml.lot_id] -= ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
            for ml in incoming_sml:
                qties_per_lot[ml.lot_id] += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
        else:
            for ml in outgoing_sml:
                qties_per_lot[ml.lot_id] += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
            for ml in incoming_sml:
                qties_per_lot[ml.lot_id] -= ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
        lot_values = []
        for lot_id, qty in qties_per_lot.items():
            if float_is_zero(qty, precision_rounding=lot_id.product_id.uom_id.rounding):
                continue
            lot_values.append({
                'product_name': lot_id.product_id.name,
                'quantity': qty,
                'uom_name': lot_id.product_uom_id.name,
                'lot_name': lot_id.name,
            })
        return lot_values


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _stock_account_get_anglo_saxon_price_unit(self):
        price_unit = super(AccountMoveLine,self)._stock_account_get_anglo_saxon_price_unit()
        # in case of anglo saxon with a product configured as invoiced based on delivery, with perpetual
        # valuation and real price costing method, we must find the real price for the cost of good sold
        if self.product_id.invoice_policy == "delivery":
            for s_line in self.sale_line_ids:
                # qtys already invoiced
                qty_done = sum([x.product_uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.move_id.state == 'posted'])
                quantity = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = s_line.move_ids.sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                average_price_unit = self._compute_average_price(qty_done, quantity, moves)
                price_unit = average_price_unit or price_unit
                price_unit = self.product_id.uom_id._compute_price(price_unit, self.product_uom_id)
        return price_unit

    def _compute_average_price(self, qty_done, quantity, moves):
        return self.env['product.product']._compute_average_price(qty_done, quantity, moves)
