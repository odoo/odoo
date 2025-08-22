# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, api
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super()._stock_account_get_last_step_stock_moves()
        for invoice in self:
            if invoice.move_type not in ['out_invoice', 'out_refund']:
                continue
            if (invoice.move_type == 'out_invoice' or (
                invoice.move_type == 'out_refund' and any(invoice.invoice_line_ids.sale_line_ids.mapped('is_downpayment')))
            ):
                rslt += invoice.mapped('invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
            else:
                rslt += invoice.mapped('reversed_entry_id.invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
                # Add refunds generated from the SO
                rslt += invoice.mapped('invoice_line_ids.sale_line_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return rslt

    def _get_invoiced_lot_values(self):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()

        res = super()._get_invoiced_lot_values()

        if self.state == 'draft' or not self.invoice_date or self.move_type not in ('out_invoice', 'out_refund'):
            return res

        current_invoice_amls = self.invoice_line_ids.filtered(lambda aml: aml.display_type == 'product' and aml.product_id and aml.product_id.type == 'consu' and aml.quantity)
        all_invoices_amls = current_invoice_amls.sale_line_ids.invoice_lines.filtered(lambda aml: aml._filter_aml_lot_valuation()).sorted(lambda aml: (aml.date, aml.move_name, aml.id))
        index = all_invoices_amls.ids.index(current_invoice_amls[:1].id) if current_invoice_amls[:1] in all_invoices_amls else 0
        previous_amls = all_invoices_amls[:index]
        invoiced_qties = current_invoice_amls._get_invoiced_qty_per_product()
        invoiced_products = invoiced_qties.keys()

        if self.move_type == 'out_invoice':
            # filter out the invoices that have been fully refund and re-invoice otherwise, the quantities would be
            # consumed by the reversed invoice and won't be print on the new draft invoice
            previous_amls = previous_amls.filtered(lambda aml: aml.move_id.payment_state != 'reversed')

        previous_qties_invoiced = previous_amls._get_invoiced_qty_per_product()

        if self.move_type == 'out_refund':
            # we swap the sign because it's a refund, and it would print negative number otherwise
            for p in previous_qties_invoiced:
                previous_qties_invoiced[p] = -previous_qties_invoiced[p]
            for p in invoiced_qties:
                invoiced_qties[p] = -invoiced_qties[p]

        qties_per_lot = defaultdict(float)
        previous_qties_delivered = defaultdict(float)
        stock_move_lines = current_invoice_amls.sale_line_ids.move_ids.move_line_ids.filtered(lambda sml: sml.state == 'done' and sml.lot_id).sorted(lambda sml: (sml.date, sml.id))
        for sml in stock_move_lines:
            if sml.product_id not in invoiced_products or not sml._should_show_lot_in_invoice():
                continue
            product = sml.product_id
            product_uom = product.uom_id
            quantity = sml.product_uom_id._compute_quantity(sml.quantity, product_uom)

            # is it a stock return considering the document type (should it be it thought of as positively or negatively?)
            is_stock_return = (
                    self.move_type == 'out_invoice' and (sml.location_id.usage, sml.location_dest_id.usage) == ('customer', 'internal')
                    or
                    self.move_type == 'out_refund' and (sml.location_id.usage, sml.location_dest_id.usage) == ('internal', 'customer')
            )
            if is_stock_return:
                returned_qty = min(qties_per_lot[sml.lot_id], quantity)
                qties_per_lot[sml.lot_id] -= returned_qty
                quantity = returned_qty - quantity

            previous_qty_invoiced = previous_qties_invoiced[product]
            previous_qty_delivered = previous_qties_delivered[product]
            # If we return more than currently delivered (i.e., quantity < 0), we remove the surplus
            # from the previously delivered (and quantity becomes zero). If it's a delivery, we first
            # try to reach the previous_qty_invoiced
            if product_uom.compare(quantity, 0) < 0 or product_uom.compare(previous_qty_delivered, previous_qty_invoiced) < 0:
                previously_done = quantity if is_stock_return else min(previous_qty_invoiced - previous_qty_delivered, quantity)
                previous_qties_delivered[product] += previously_done
                quantity -= previously_done

            qties_per_lot[sml.lot_id] += quantity

        for lot, qty in qties_per_lot.items():
            # access the lot as a superuser in order to avoid an error
            # when a user prints an invoice without having the stock access
            lot = lot.sudo()
            if lot.product_uom_id.is_zero(invoiced_qties[lot.product_id]) or lot.product_uom_id.compare(qty, 0) <= 0:
                continue
            invoiced_lot_qty = min(qty, invoiced_qties[lot.product_id])
            invoiced_qties[lot.product_id] -= invoiced_lot_qty
            res.append({
                'product_name': lot.product_id.display_name,
                'quantity': formatLang(self.env, invoiced_lot_qty, dp='Product Unit'),
                'uom_name': lot.product_uom_id.name,
                'lot_name': lot.name,
                # The lot id is needed by localizations to inherit the method and add custom fields on the invoice's report.
                'lot_id': lot.id,
            })

        return res

    @api.depends('line_ids.sale_line_ids.order_id.effective_date')
    def _compute_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_delivery_date()
        for move in self:
            sale_order_effective_date = list(filter(None, move.line_ids.sale_line_ids.order_id.mapped('effective_date')))
            effective_date_res = max(sale_order_effective_date) if sale_order_effective_date else False
            # if multiple sale order we take the bigger effective_date
            if effective_date_res:
                move.delivery_date = effective_date_res

    @api.depends('line_ids.sale_line_ids.order_id')
    def _compute_incoterm_location(self):
        super()._compute_incoterm_location()
        for move in self:
            sale_locations = move.line_ids.sale_line_ids.order_id.mapped('incoterm_location')
            incoterm_res = next((incoterm for incoterm in sale_locations if incoterm), False)
            # if multiple purchase order we take an incoterm that is not false
            if incoterm_res:
                move.incoterm_location = incoterm_res

    def _get_anglo_saxon_price_ctx(self):
        ctx = super()._get_anglo_saxon_price_ctx()
        move_is_downpayment = self.invoice_line_ids.filtered(
            lambda line: any(line.sale_line_ids.mapped("is_downpayment"))
        )
        return dict(ctx, move_is_downpayment=move_is_downpayment)

    def _get_protected_vals(self, vals, records):
        res = super()._get_protected_vals(vals, records)
        # `delivery_date` should be protected on any account.move/account.move.line write
        perma_protected = {self._fields['delivery_date']}
        if records._name == self._name:
            res.append((perma_protected, records))
        elif records._name == self.line_ids._name:
            res.append((perma_protected, records.move_id))
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_stock_moves(self):
        return super()._get_stock_moves() | self.sale_line_ids.move_ids

    def _sale_can_be_reinvoice(self):
        self.ensure_one()
        return self.move_type != 'entry' and self.display_type != 'cogs' and super()._sale_can_be_reinvoice()
