# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_valued_in_moves(self):
        self.ensure_one()
        return self.purchase_line_id.move_ids.filtered(
            lambda m: m.state == 'done' and m.product_qty != 0)

    def _get_out_and_not_invoiced_qty(self, in_moves):
        self.ensure_one()
        if not in_moves:
            return 0
        aml_qty = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
        invoiced_qty = sum(line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
                           for line in self.purchase_line_id.invoice_lines - self)
        layers = in_moves.stock_valuation_layer_ids
        layers_qty = sum(layers.mapped('quantity'))
        out_qty = layers_qty - sum(layers.mapped('remaining_qty'))
        total_out_and_not_invoiced_qty = max(0, out_qty - invoiced_qty)
        out_and_not_invoiced_qty = min(aml_qty, total_out_and_not_invoiced_qty)
        return self.product_id.uom_id._compute_quantity(out_and_not_invoiced_qty, self.product_uom_id)

    def _get_price_diff_account(self):
        self.ensure_one()
        if self.product_id.cost_method == 'standard':
            return False
        accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=self.move_id.fiscal_position_id)
        return accounts['expense']

    def _create_in_invoice_svl(self):
        svl_vals_list = []
        for line in self:
            line = line.with_company(line.company_id)
            move = line.move_id.with_company(line.move_id.company_id)
            po_line = line.purchase_line_id
            uom = line.product_uom_id or line.product_id.uom_id

            # Don't create value for more quantity than received
            quantity = po_line.qty_received - (po_line.qty_invoiced - line.quantity)
            quantity = max(min(line.quantity, quantity), 0)
            if float_is_zero(quantity, precision_rounding=uom.rounding):
                continue

            layers = line._get_stock_valuation_layers(move)
            # Retrieves SVL linked to a return.
            if not layers:
                continue

            price_unit = line._get_gross_unit_price()
            price_unit = line.currency_id._convert(price_unit, line.company_id.currency_id, line.company_id, line.date, round=False)
            price_unit = line.product_uom_id._compute_price(price_unit, line.product_id.uom_id)
            layers_price_unit = line._get_stock_valuation_layers_price_unit(layers)
            layers_to_correct = line._get_stock_layer_price_difference(layers, layers_price_unit, price_unit)
            svl_vals_list += line._prepare_in_invoice_svl_vals(layers_to_correct)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _get_stock_valuation_layers_price_unit(self, layers):
        price_unit_by_layer = {}
        for layer in layers:
            price_unit_by_layer[layer] = layer.value / layer.quantity
        return price_unit_by_layer

    def _get_stock_layer_price_difference(self, layers, layers_price_unit, price_unit):
        self.ensure_one()
        po_line = self.purchase_line_id
        aml_qty = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
        invoice_lines = po_line.invoice_lines - self
        invoices_qty = 0
        for invoice_line in invoice_lines:
            invoices_qty += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, invoice_line.product_id.uom_id)
        qty_received = po_line.product_uom._compute_quantity(po_line.qty_received, self.product_id.uom_id)
        out_qty = qty_received - sum(layers.mapped('remaining_qty'))
        out_and_not_billed_qty = max(0, out_qty - invoices_qty)
        total_to_correct = max(0, aml_qty - out_and_not_billed_qty)
        # we also need to skip the remaining qty that is already billed
        total_to_skip = max(0, invoices_qty - out_qty)
        layers_to_correct = {}
        for layer in layers:
            if float_compare(total_to_correct, 0, precision_rounding=self.product_id.uom_id.rounding) <= 0:
                break
            remaining_qty = layer.remaining_qty
            qty_to_skip = min(total_to_skip, remaining_qty)
            remaining_qty = max(0, remaining_qty - qty_to_skip)
            qty_to_correct = min(total_to_correct, remaining_qty)
            total_to_skip -= qty_to_skip
            total_to_correct -= qty_to_correct
            unit_valuation_difference = price_unit - layers_price_unit[layer]
            if float_is_zero(unit_valuation_difference * qty_to_correct, precision_rounding=self.company_id.currency_id.rounding):
                continue
            po_pu_curr = po_line.currency_id._convert(po_line.price_unit, self.currency_id, self.company_id, self.date, round=False)
            price_difference_curr = po_pu_curr - self._get_gross_unit_price()
            layers_to_correct[layer] = (qty_to_correct, unit_valuation_difference, price_difference_curr)
        return layers_to_correct

    def _prepare_in_invoice_svl_vals(self, layers_correction):
        svl_vals_list = []
        invoiced_qty = self.quantity
        common_svl_vals = {
            'account_move_id': self.move_id.id,
            'account_move_line_id': self.id,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'quantity': 0,
            'unit_cost': 0,
            'remaining_qty': 0,
            'remaining_value': 0,
            'description': self.move_id.name and '%s - %s' % (self.move_id.name, self.product_id.name) or self.product_id.name,
        }
        for layer, (quantity, price_difference, price_difference_curr) in layers_correction.items():
            svl_vals = self.product_id._prepare_in_svl_vals(quantity, price_difference)
            diff_value_curr = self.currency_id.round(price_difference_curr * quantity)
            svl_vals.update(**common_svl_vals, stock_valuation_layer_id=layer.id, price_diff_value=diff_value_curr)
            svl_vals_list.append(svl_vals)
            # Adds the difference into the last SVL's remaining value.
            layer.remaining_value += svl_vals['value']
            if float_compare(invoiced_qty, 0, self.product_id.uom_id.rounding) <= 0:
                break

        return svl_vals_list
