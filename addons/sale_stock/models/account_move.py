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
            rslt += invoice.mapped('invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
        for invoice in self.filtered(lambda x: x.type == 'out_refund'):
            rslt += invoice.mapped('reversed_entry_id.invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
            # Add refunds generated from the SO
            rslt += invoice.mapped('invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return rslt

    def _get_invoiced_lot_values(self):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()
        FloatFormat = self.env['ir.qweb.field.float']
        dp = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        if self.state == 'draft' or not self.invoice_date or self.type not in ('out_invoice', 'out_refund'):
            return []

        lot_values = []

        for line in self.invoice_line_ids.filtered(
                lambda x: not x.display_type and x.product_id and x.quantity and x.product_id.tracking != 'none'):

            product = line.product_id
            product_uom = product.uom_id
            product_rounding = product_uom.rounding
            previous_aml = line.sale_line_ids.invoice_lines.filtered(
                lambda x: x.move_id != self and x.move_id.state not in ('draft', 'cancel')
                and x.product_id == product
                and x.move_id.invoice_date and x.move_id.invoice_date <= self.invoice_date)

            previous_qty_invoiced = 0
            for aml in previous_aml:
                qty = aml.product_uom_id._compute_quantity(aml.quantity, product_uom)
                if aml.move_id.move_type == 'out_invoice':
                    previous_qty_invoiced += qty
                elif aml.move_id.move_type == 'out_refund':
                    previous_qty_invoiced -= qty

            smls = line.sale_line_ids.move_ids.move_line_ids.filtered(
                lambda x: x.state == 'done' and x.lot_id and x.product_id == product)\
                .sorted(lambda x: (x.date, x.id))

            save_invoiced_qty = line.product_uom_id._compute_quantity(
                line.quantity, product_uom) * (1 if line.move_id.move_type == 'out_invoice' else -1)
            invoiced_qty = save_invoiced_qty

            qties_per_lot = defaultdict(float)
            for sml in smls:
                qty_done = sml.product_uom_id._compute_quantity(sml.qty_done, product_uom)
                if fields.Float.compare(previous_qty_invoiced, 0, precision_rounding=product_rounding) > 0:
                    if fields.Float.compare(qty_done, previous_qty_invoiced, precision_rounding=product_rounding) > 0:
                        qties_per_lot[(sml.product_uom_id, sml.lot_id)] += qty_done - previous_qty_invoiced

                    if sml.location_id.usage == 'customer':
                        previous_qty_invoiced += qty_done
                    elif sml.location_dest_id.usage == 'customer':
                        previous_qty_invoiced -= qty_done

                elif fields.Float.compare(invoiced_qty, 0, precision_rounding=product_rounding) > 0:
                    if sml.location_id.usage == 'customer':
                        invoiced_qty += qty_done
                    elif sml.location_dest_id.usage == 'customer':
                        invoiced_qty -= qty_done
                    qties_per_lot[(sml.product_uom_id, sml.lot_id)] += qty_done
                else:
                    break

            invoiced_qty = save_invoiced_qty
            for key, qty in qties_per_lot.items():
                uom, lot = key
                if float_is_zero(qty, precision_rounding=product_rounding):
                    continue
                lot_values.append({
                    'product_name': lot.product_id.display_name,
                    'quantity': FloatFormat.value_to_html(product_uom._compute_quantity(min(qty, invoiced_qty), uom), {'precision': dp}),
                    'uom_name': uom.name,
                    'lot_name': lot.name,
                    # The lot id is needed by localizations to inherit the method and add custom fields on the invoice's report.
                    'lot_id': lot.id
                })
                invoiced_qty -= qty
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

            average_price_unit = self.product_id.with_context(force_company=self.company_id.id, is_returned=is_line_reversing)._compute_average_price(qty_invoiced, qty_to_invoice, so_line.move_ids)
            price_unit = average_price_unit or price_unit
            price_unit = self.product_id.uom_id.with_context(force_company=self.company_id.id)._compute_price(price_unit, self.product_uom_id)
        return price_unit
