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

            layers = line._get_valued_in_moves().stock_valuation_layer_ids.filtered(lambda svl: svl.product_id == line.product_id and not svl.stock_valuation_layer_id)
            if not layers:
                continue

            new_svl_vals_list, new_aml_vals_list = line._generate_price_difference_vals(layers)
            svl_vals_list += new_svl_vals_list
            aml_vals_list += new_aml_vals_list
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list), self.env['account.move.line'].sudo().create(aml_vals_list)

    def _generate_price_difference_vals(self, layers):
        """
        The method will determine which layers are impacted by the AML (`self`) and, in case of a price difference, it
        will then return the values of the new AMLs and SVLs
        """
        self.ensure_one()
        po_line = self.purchase_line_id
        product_uom = self.product_id.uom_id

        # `history` is a list of tuples: (time, aml, layer)
        # aml and layer will never be both defined
        # we use this to get an order between posted AML and layers
        history = [(layer.create_date, False, layer) for layer in layers]
        am_state_field = self.env['ir.model.fields'].search([('model', '=', 'account.move'), ('name', '=', 'state')], limit=1)
        for aml in po_line.invoice_lines:
            move = aml.move_id
            if move.state != 'posted':
                continue
            state_trackings = move.message_ids.tracking_value_ids.filtered(lambda t: t.field_id == am_state_field).sorted('id')
            time = state_trackings[-1:].create_date or move.create_date  # `or` in case it has been created in posted state
            history.append((time, aml, False))
        # Sort history based on the datetime. In case of equality, the prority is given to SVLs, then to IDs.
        # That way, we ensure a deterministic behaviour
        history.sort(key=lambda item: (item[0], bool(item[1]), (item[1] or item[2]).id))

        # Replay the whole history: we want to know what are the links between each layer and each invoice,
        # and then the links between `self` and the layers
        qty_to_invoice_per_layer, layers_and_invoices_qties = self._replay_history(layers, history)

        # Now we know what layers does `self` use, let's check if we have to create a pdiff SVL
        # (or cancel such an SVL in case of a refund)
        invoice = self.move_id
        svl_vals_list = []
        aml_vals_list = []
        for layer in layers:
            # use the link between `self` and `layer` (i.e. the qty of `layer` billed by `self`)
            invoicing_layer_qty = layers_and_invoices_qties[(layer, invoice)][1]
            if float_is_zero(invoicing_layer_qty, precision_rounding=product_uom.rounding):
                continue

            # We will only consider the total quantity to invoice of the layer because we don't
            # want to invoice a part of the layer that has not been invoiced and that has been
            # returned in the meantime
            total_layer_qty_to_invoice = qty_to_invoice_per_layer[layer][0]
            remaining_qty = layer.remaining_qty
            out_layer_qty = total_layer_qty_to_invoice - remaining_qty
            if self.is_refund:
                sign = -1
                reversed_invoice = invoice.reversed_entry_id
                if not reversed_invoice:
                    # this is a refund for a returned quantity, we don't have anything to do
                    continue
                initial_invoiced_qty = layers_and_invoices_qties[(layer, reversed_invoice)][0]
                initial_pdiff_svl = layer.stock_valuation_layer_ids.filtered(lambda svl: svl.account_move_line_id.move_id == reversed_invoice)
                if not initial_pdiff_svl or float_is_zero(initial_invoiced_qty, precision_rounding=product_uom.rounding):
                    continue
                # We have an already-out quantity: we must skip the part already invoiced. So, first,
                # let's compute the already invoiced quantity...
                previously_invoiced_qty = 0
                for item in history:
                    previous_aml = item[1]
                    if not previous_aml or previous_aml.is_refund:
                        continue
                    previous_invoice = previous_aml.move_id
                    if previous_invoice == reversed_invoice:
                        break
                    previously_invoiced_qty += layers_and_invoices_qties[(layer, previous_invoice,)][1]
                # ... Second, skip it:
                out_qty_to_invoice = max(0, out_layer_qty - previously_invoiced_qty)
                qty_to_correct = max(0, invoicing_layer_qty - out_qty_to_invoice)
                if out_qty_to_invoice:
                    # In case the out qty is different from the one posted by the initial bill, we should compensate
                    # this quantity with debit/credit between stock_in and expense, but we are reversing an initial
                    # invoice and don't want to do more than the original one
                    out_qty_to_invoice = 0
                aml = initial_pdiff_svl.account_move_line_id
                parent_layer = initial_pdiff_svl.stock_valuation_layer_id
                layer_price_unit = parent_layer._get_layer_price_unit()
            else:
                sign = 1
                # get the invoiced qty of the layer without considering `self`
                invoiced_layer_qty = total_layer_qty_to_invoice - qty_to_invoice_per_layer[layer][1] - invoicing_layer_qty
                remaining_out_qty_to_invoice = max(0, out_layer_qty - invoiced_layer_qty)
                out_qty_to_invoice = min(remaining_out_qty_to_invoice, invoicing_layer_qty)
                qty_to_correct = invoicing_layer_qty - out_qty_to_invoice
                layer_price_unit = layer._get_layer_price_unit()

                returned_move = layer.stock_move_id.origin_returned_move_id
                if returned_move and returned_move._is_out() and returned_move._is_returned(valued_type='out'):
                    # Odd case! The user receives a product, then returns it. The returns are processed as classic
                    # output, so the value of the returned product can be different from the initial one. The user
                    # then receives again the returned product (that's where we are here) -> the SVL is based on
                    # the returned one, the accounting entries are already compensated, and we don't want to impact
                    # the stock valuation. So, let's fake the layer price unit with the POL one as everything is
                    # already ok
                    layer_price_unit = po_line.currency_id._convert(
                        po_line._get_gross_price_unit(),
                        layer.currency_id,
                        layer.company_id,
                        layer.create_date.date(),
                        round=False
                    )
                aml = self

            svl_vals, aml_vals = self._prepare_pdiff_vals(layer, aml, layer_price_unit, out_qty_to_invoice, sign * qty_to_correct)
            svl_vals_list.extend(svl_vals)
            aml_vals_list.extend(aml_vals)

        return svl_vals_list, aml_vals_list

    def _replay_history(self, layers, history):
        history.append((False, self, False))  # time was only usefull for the sorting

        # the next dict is a matrix [layer L, invoice I] where each cell gives two info:
        # [initial qty of L invoiced by I, remaining invoiced qty]
        # the second info is usefull in case of a refund
        layers_and_invoices_qties = defaultdict(lambda: [0, 0])

        # the next dict will also provide two info:
        # [total qty to invoice, remaining qty to invoice]
        # we need the total qty to invoice, so we will be able to deduce the invoiced qty before `self`
        qty_to_invoice_per_layer = defaultdict(lambda: [0, 0])
        for _time, aml, layer in history:
            if layer:
                total_layer_qty_to_invoice = abs(layer.quantity)
                initial_layer = layer.stock_move_id.origin_returned_move_id.stock_valuation_layer_ids
                # Filter out revaluation layers (Landed Cost)
                initial_layer = initial_layer.filtered(lambda svl: not svl.stock_valuation_layer_id)
                if initial_layer:
                    # `layer` is a return. We will cancel the qty to invoice of the returned layer
                    # /!\ we will cancel the qty not yet invoiced only
                    initial_layer_remaining_qty = qty_to_invoice_per_layer[initial_layer][1]
                    common_qty = min(initial_layer_remaining_qty, total_layer_qty_to_invoice)
                    qty_to_invoice_per_layer[initial_layer][0] -= common_qty
                    qty_to_invoice_per_layer[initial_layer][1] -= common_qty
                    total_layer_qty_to_invoice = max(0, total_layer_qty_to_invoice - common_qty)
                if float_compare(total_layer_qty_to_invoice, 0, precision_rounding=self.product_id.uom_id.rounding) > 0:
                    qty_to_invoice_per_layer[layer] = [total_layer_qty_to_invoice, total_layer_qty_to_invoice]
            else:
                invoice = aml.move_id
                impacted_invoice = False
                aml_qty = aml.product_uom_id._compute_quantity(aml.quantity, self.product_id.uom_id)
                if aml.is_refund:
                    reversed_invoice = aml.move_id.reversed_entry_id
                    if reversed_invoice:
                        sign = -1
                        impacted_invoice = reversed_invoice
                        # it's a refund, therefore we can only consume the quantities invoiced by
                        # the initial invoice (`reversed_invoice`)
                        layers_to_consume = []
                        for layer in layers:
                            remaining_invoiced_qty = layers_and_invoices_qties[layer, reversed_invoice][1]
                            layers_to_consume.append((layer, remaining_invoiced_qty))
                    else:
                        # the refund has been generated because of a stock return, let's find and use it
                        sign = 1
                        layers_to_consume = []
                        for layer in qty_to_invoice_per_layer:
                            if layer.stock_move_id._is_out():
                                layers_to_consume.append((layer, qty_to_invoice_per_layer[layer][1]))
                else:
                    # classic case, we are billing a received quantity so let's use the incoming SVLs
                    sign = 1
                    layers_to_consume = []
                    for layer in qty_to_invoice_per_layer:
                        if layer.stock_move_id._is_in():
                            layers_to_consume.append((layer, qty_to_invoice_per_layer[layer][1]))
                while float_compare(aml_qty, 0, precision_rounding=self.product_id.uom_id.rounding) > 0 and layers_to_consume:
                    layer, total_layer_qty_to_invoice = layers_to_consume[0]
                    layers_to_consume = layers_to_consume[1:]
                    if float_is_zero(total_layer_qty_to_invoice, precision_rounding=self.product_id.uom_id.rounding):
                        continue
                    common_qty = min(aml_qty, total_layer_qty_to_invoice)
                    aml_qty -= common_qty
                    qty_to_invoice_per_layer[layer][1] -= sign * common_qty
                    layers_and_invoices_qties[layer, invoice] = [common_qty, common_qty]
                    layers_and_invoices_qties[layer, impacted_invoice][1] -= common_qty

        return qty_to_invoice_per_layer, layers_and_invoices_qties

    def _prepare_pdiff_vals(self, layer, aml, layer_price_unit, out_qty_to_invoice, qty_to_correct):
        svl_vals_list = []
        aml_vals_list = []

        aml_gross_price_unit = aml._get_gross_unit_price()
        # convert from aml currency to company currency
        aml_price_unit = aml_gross_price_unit / aml.currency_rate
        aml_price_unit = aml.product_uom_id._compute_price(aml_price_unit, self.product_id.uom_id)

        unit_valuation_difference = aml_price_unit - layer_price_unit
        precision_digits = max(
            aml.currency_id.decimal_places,
            layer.currency_id.decimal_places,
            self.env['decimal.precision'].precision_get('Product Price'),
        )
        if float_is_zero(unit_valuation_difference, precision_digits=precision_digits):
            unit_valuation_difference = 0

        # Generate the AML values for the already out quantities
        # convert from company currency to aml currency
        unit_valuation_difference_curr = unit_valuation_difference * self.currency_rate
        unit_valuation_difference_curr = self.product_id.uom_id._compute_price(unit_valuation_difference_curr, self.product_uom_id)
        out_qty_to_invoice = self.product_id.uom_id._compute_quantity(out_qty_to_invoice, self.product_uom_id)
        if (
            not self.currency_id.is_zero(unit_valuation_difference_curr * out_qty_to_invoice) and
            self.product_id.valuation == 'real_time'
        ):
            aml_vals_list += self._prepare_pdiff_aml_vals(out_qty_to_invoice, unit_valuation_difference_curr)

        # Generate the SVL values for the on hand quantities (and impact the parent layer)
        po_pu_curr = self.purchase_line_id.currency_id._convert(
            self.purchase_line_id.price_unit,
            self.currency_id,
            self.company_id,
            self.move_id.invoice_date or self.date or fields.Date.context_today(self),
            round=False
        )
        price_difference_curr = po_pu_curr - aml_gross_price_unit
        if not float_is_zero(unit_valuation_difference * qty_to_correct, precision_rounding=self.company_id.currency_id.rounding):
            svl_vals = self._prepare_pdiff_svl_vals(layer, qty_to_correct, unit_valuation_difference, price_difference_curr)
            layer.remaining_value += svl_vals['value']
            svl_vals_list.append(svl_vals)

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
                'balance': self.company_id.currency_id.round((qty * price * sign) / self.currency_rate),
                'account_id': account.id,
                'analytic_distribution': self.analytic_distribution,
                'display_type': 'cogs',
            })
        return vals_list

    def _prepare_pdiff_svl_vals(self, corrected_layer, quantity, unit_cost, pdiff):
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
            **self.product_id._prepare_in_svl_vals(quantity, unit_cost, corrected_layer.lot_id),
            **common_svl_vals,
            'stock_valuation_layer_id': corrected_layer.id,
            'price_diff_value': self.currency_id.round(pdiff * quantity),
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
