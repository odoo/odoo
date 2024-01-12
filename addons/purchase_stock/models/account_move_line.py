# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.float_utils import float_compare, float_is_zero

from collections import defaultdict


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

    def _apply_price_difference(self):
        svl_vals_list = []
        aml_vals_list = []
        for line in self:
            line = line.with_company(line.company_id)
            po_line = line.purchase_line_id
            uom = line.product_uom_id or line.product_id.uom_id

            # Don't create value for more quantity than received
            quantity = po_line.qty_received - (po_line.qty_invoiced - line.quantity)
            quantity = max(min(line.quantity, quantity), 0)
            if float_is_zero(quantity, precision_rounding=uom.rounding):
                continue

            new_svl_vals_list, new_aml_vals_list = line._generate_price_difference_vals()
            svl_vals_list += new_svl_vals_list
            aml_vals_list += new_aml_vals_list
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list), self.env['account.move.line'].sudo().create(aml_vals_list)

    def _calculate_unit_price_difference(self, svl):
        """
            Return the unit price difference between this line and the provided SVL.
        """
        layer_price_unit = svl._get_layer_price_unit()
        aml_gross_price_unit = self._get_gross_unit_price()
        aml_price_unit = aml_gross_price_unit / self.currency_rate
        aml_price_unit = self.product_uom_id._compute_price(aml_price_unit, self.product_id.uom_id)
        return aml_price_unit - layer_price_unit

    def _generate_correction_amls(self, price_diff, qty):
        """
            Convert the price_diff and qty to the correct currency and uom,
            and return the values for AML entries that need to be created.
        """
        unit_valuation_difference_curr = price_diff * self.currency_rate
        unit_valuation_difference_curr = self.product_id.uom_id._compute_price(unit_valuation_difference_curr, self.product_uom_id)
        out_qty_to_invoice = self.product_id.uom_id._compute_quantity(qty, self.product_uom_id)
        if not float_is_zero(unit_valuation_difference_curr * out_qty_to_invoice, precision_rounding=self.currency_id.rounding):
            return self._prepare_pdiff_aml_vals(out_qty_to_invoice, unit_valuation_difference_curr)

    def _generate_correction_svls(self, price_diff, qty, parent_layer, price_diff_curr, valued_in, valued_out):
        """
            Return the values for creating for a correction SVL based on the provided values
            and update the remaining value of the parent layer.
            In case the value of the SVL would be 0, we make sure it is an empty layer.
        """
        if float_is_zero(price_diff * qty, precision_rounding=self.company_id.currency_id.rounding):
            # Set all to 0 to create an empty SVL
            svl_vals = self._prepare_pdiff_svl_vals(parent_layer, 0, 0, 0, valued_in, valued_out)
        else:
            svl_vals = self._prepare_pdiff_svl_vals(parent_layer, qty, price_diff, price_diff_curr, valued_in, valued_out)
            parent_layer.remaining_value += svl_vals['value']
        return svl_vals

    def _generate_price_difference_vals(self):
        self.ensure_one()
        product_uom = self.product_id.uom_id
        po_line = self.purchase_line_id
        po_pu_curr = po_line.currency_id._convert(po_line.price_unit, self.currency_id, self.company_id, self.move_id.invoice_date or self.date or fields.Date.context_today(self), round=False)
        svl_vals_list = []
        aml_vals_list = []
        remaining_bill_qty = self.product_uom_id._compute_quantity(self.qty_to_value, product_uom) # Make sure to work in product UoM instead of invoice UoM

        if self.is_refund:
            reversed_invoice = self.move_id.reversed_entry_id
            if reversed_invoice:
                initial_aml = po_line.invoice_lines.filtered(lambda aml: aml.move_id == reversed_invoice)
            else:
                # This refund was created manually without a linked initial invoice, we try to find one manually
                initial_aml = next((aml for aml in po_line.invoice_lines if aml != self and not aml.is_refund), None)
                if not initial_aml:
                    return (), ()
            price_difference_curr = po_pu_curr - initial_aml._get_gross_unit_price()
            for correction_svl in initial_aml.stock_valuation_layer_ids:
                if float_is_zero(remaining_bill_qty, precision_rounding=product_uom.rounding):
                    break

                parent_layer = correction_svl.stock_valuation_layer_id
                original_pdiff = initial_aml._calculate_unit_price_difference(parent_layer)

                overvalued, still_in, meanwhile_out, already_out = correction_svl.calculate_refund_quantities(remaining_bill_qty)
                remaining_bill_qty -= overvalued + still_in + meanwhile_out + already_out

                to_compensate_in = still_in + overvalued + meanwhile_out
                to_compensate_out = already_out + meanwhile_out
                svl_vals = self._generate_correction_svls(original_pdiff, -still_in, parent_layer, price_difference_curr, -to_compensate_in, -to_compensate_out)
                if svl_vals:
                    svl_vals_list.append(svl_vals)

                if float_is_zero(meanwhile_out, precision_rounding=product_uom.rounding):
                    aml_vals = self._generate_correction_amls(original_pdiff, -already_out)
                    if aml_vals:
                        aml_vals_list += aml_vals
        else:
            price_difference_curr = po_pu_curr - self._get_gross_unit_price()
            for layer in self._get_valued_in_moves().stock_valuation_layer_ids.filtered(lambda svl: svl.product_id == self.product_id and not svl.stock_valuation_layer_id):
                if float_is_zero(remaining_bill_qty, precision_rounding=product_uom.rounding):
                    break

                if float_compare(layer.qty_to_value_already_out + layer.qty_to_value_in_stock, 0, precision_rounding=product_uom.rounding) <= 0:
                    continue

                unit_valuation_difference = self._calculate_unit_price_difference(layer)

                already_out = min(remaining_bill_qty, layer.qty_to_value_already_out)
                remaining_bill_qty -= already_out

                still_in = min(remaining_bill_qty, layer.qty_to_value_in_stock)
                remaining_bill_qty -= still_in

                svl_vals = self._generate_correction_svls(unit_valuation_difference, still_in, layer, price_difference_curr, still_in, already_out)
                if svl_vals:
                    svl_vals_list.append(svl_vals)

                aml_vals = self._generate_correction_amls(unit_valuation_difference, already_out)
                if aml_vals:
                    aml_vals_list += aml_vals

        return svl_vals_list, aml_vals_list

    def _prepare_pdiff_aml_vals(self, qty, unit_valuation_difference):
        self.ensure_one()
        vals_list = []

        sign = self.move_id.direction_sign
        expense_account = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=self.move_id.fiscal_position_id)['expense']
        if not expense_account:
            return vals_list

        for price, account in [
            (unit_valuation_difference, expense_account),
            (-unit_valuation_difference, self.account_id),
        ]:
            vals_list.append({
                'name': self.name[:64],
                'move_id': self.move_id.id,
                'partner_id': self.partner_id.id or self.move_id.commercial_partner_id.id,
                'currency_id': self.currency_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'quantity': qty,
                'price_unit': price,
                'price_subtotal': qty * price,
                'amount_currency': qty * price * sign,
                'balance': self.currency_id._convert(
                    qty * price * sign,
                    self.company_currency_id,
                    self.company_id, fields.Date.today(),
                ),
                'account_id': account.id,
                'analytic_distribution': self.analytic_distribution,
                'display_type': 'cogs',
            })
        return vals_list

    def _prepare_pdiff_svl_vals(self, corrected_layer, quantity, unit_cost, pdiff, valued_in, valued_out):
        self.ensure_one()
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
        return {
            **self.product_id._prepare_in_svl_vals(quantity, unit_cost),
            **common_svl_vals,
            'stock_valuation_layer_id': corrected_layer.id,
            'price_diff_value': self.currency_id.round(pdiff * quantity),
            'qty_valued_in_stock': valued_in,
            'qty_valued_already_out': valued_out,
            'is_dummy': quantity == 0 and unit_cost == 0,
        }

    def _get_price_unit_val_dif_and_relevant_qty(self):
        self.ensure_one()
        # Retrieve stock valuation moves.
        valuation_stock_moves = self.env['stock.move'].search([
            ('purchase_line_id', '=', self.purchase_line_id.id),
            ('state', '=', 'done'),
            ('product_qty', '!=', 0.0),
        ]) if self.purchase_line_id else self.env['stock.move']

        if self.product_id.cost_method != 'standard' and self.purchase_line_id:
            if self.move_type == 'in_refund':
                valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_out())
            else:
                valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_in())

            if not valuation_stock_moves:
                return 0, 0

            valuation_price_unit_total, valuation_total_qty = valuation_stock_moves._get_valuation_price_and_qty(self, self.move_id.currency_id)
            valuation_price_unit = valuation_price_unit_total / valuation_total_qty
            valuation_price_unit = self.product_id.uom_id._compute_price(valuation_price_unit, self.product_uom_id)
        else:
            # Valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
            price_unit = self.product_id.uom_id._compute_price(self.product_id.standard_price, self.product_uom_id)
            price_unit = -price_unit if self.move_id.move_type == 'in_refund' else price_unit
            valuation_date = valuation_stock_moves and max(valuation_stock_moves.mapped('date')) or self.date
            valuation_price_unit = self.company_currency_id._convert(
                price_unit, self.currency_id,
                self.company_id, valuation_date, round=False
            )

        price_unit = self._get_gross_unit_price()

        price_unit_val_dif = price_unit - valuation_price_unit
        # If there are some valued moves, we only consider their quantity already used
        if self.product_id.cost_method == 'standard':
            relevant_qty = self.quantity
        else:
            relevant_qty = self._get_out_and_not_invoiced_qty(valuation_stock_moves)

        return price_unit_val_dif, relevant_qty
