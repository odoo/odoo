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
        for invoice in self.filtered(lambda x: x.move_type == 'out_invoice'):
            rslt += invoice.mapped('invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
        for invoice in self.filtered(lambda x: x.move_type == 'out_refund'):
            rslt += invoice.mapped('reversed_entry_id.invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
            # Add refunds generated from the SO
            rslt += invoice.mapped('invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return rslt

    def _get_invoiced_lot_values(self):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()

        res = super(AccountMove, self)._get_invoiced_lot_values()

        if self.state == 'draft':
            return res

        sale_lines = self.invoice_line_ids.sale_line_ids
        sale_orders = sale_lines.order_id
        stock_move_lines = sale_lines.move_ids.filtered(lambda r: r.state == 'done').move_line_ids

        # Get the other customer invoices and refunds.
        ordered_invoice_ids = sale_orders.mapped('invoice_ids')\
            .filtered(lambda i: i.state not in ['draft', 'cancel'])\
            .sorted(lambda i: (i.invoice_date, i.id))

        # Get the position of self in other customer invoices and refunds.
        self_index = None
        i = 0
        for invoice in ordered_invoice_ids:
            if invoice.id == self.id:
                self_index = i
                break
            i += 1

        # Get the previous invoices if any.
        previous_invoices = ordered_invoice_ids[:self_index]

        # Get the incoming and outgoing sml between self.invoice_date and the previous invoice (if any) of the related product.
        write_dates = [wd for wd in self.invoice_line_ids.mapped('write_date') if wd]
        self_datetime = max(write_dates) if write_dates else None
        last_invoice_datetime = dict()
        for product in self.invoice_line_ids.product_id:
            last_invoice = previous_invoices.filtered(lambda inv: product in inv.invoice_line_ids.product_id)
            last_invoice = last_invoice[-1] if len(last_invoice) else None
            last_write_dates = last_invoice and [wd for wd in last_invoice.invoice_line_ids.mapped('write_date') if wd]
            last_invoice_datetime[product] = max(last_write_dates) if last_write_dates else None

        def _filter_incoming_sml(ml):
            if ml.state == 'done' and ml.location_id.usage == 'customer' and ml.lot_id:
                last_date = last_invoice_datetime.get(ml.product_id)
                if last_date:
                    return last_date <= ml.date <= self_datetime
                else:
                    return ml.date <= self_datetime
            return False

        def _filter_outgoing_sml(ml):
            if ml.state == 'done' and ml.location_dest_id.usage == 'customer' and ml.lot_id:
                last_date = last_invoice_datetime.get(ml.product_id)
                if last_date:
                    return last_date <= ml.date <= self_datetime
                else:
                    return ml.date <= self_datetime
            return False

        incoming_sml = stock_move_lines.filtered(_filter_incoming_sml)
        outgoing_sml = stock_move_lines.filtered(_filter_outgoing_sml)

        # Prepare and return lot_values
        qties_per_lot = defaultdict(lambda: 0)
        if self.move_type == 'out_refund':
            for ml in outgoing_sml:
                qties_per_lot[ml.lot_id] -= ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
            for ml in incoming_sml:
                qties_per_lot[ml.lot_id] += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
        else:
            for ml in outgoing_sml:
                qties_per_lot[ml.lot_id] += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
            for ml in incoming_sml:
                qties_per_lot[ml.lot_id] -= ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
        lot_values = res
        for lot_id, qty in qties_per_lot.items():
            if float_is_zero(qty, precision_rounding=lot_id.product_id.uom_id.rounding):
                continue
            lot_values.append({
                'product_name': lot_id.product_id.display_name,
                'quantity': self.env['ir.qweb.field.float'].value_to_html(qty, {'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure')}),
                'uom_name': lot_id.product_uom_id.name,
                'lot_name': lot_id.name,
                # The lot id is needed by localizations to inherit the method and add custom fields on the invoice's report.
                'lot_id': lot_id.id
            })
        return lot_values


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _sale_can_be_reinvoice(self):
        self.ensure_one()
        return not self.is_anglo_saxon_line and super(AccountMoveLine, self)._sale_can_be_reinvoice()

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()

        so_line = self.sale_line_ids and self.sale_line_ids[-1] or False
        if so_line:
            is_line_reversing = bool(self.move_id.reversed_entry_id)
            qty_to_invoice = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            posted_invoice_lines = so_line.invoice_lines.filtered(lambda l: l.move_id.state == 'posted' and bool(l.move_id.reversed_entry_id) == is_line_reversing)
            qty_invoiced = sum([x.product_uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in posted_invoice_lines])

            product = self.product_id.with_company(self.company_id).with_context(is_returned=is_line_reversing)
            average_price_unit = product._compute_average_price(qty_invoiced, qty_to_invoice, so_line.move_ids)
            if average_price_unit:
                price_unit = self.product_id.uom_id.with_company(self.company_id)._compute_price(average_price_unit, self.product_uom_id)
        return price_unit
