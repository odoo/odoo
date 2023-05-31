# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_compare, float_is_zero
from odoo.tools.misc import groupby


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        ''' Prepare values used to create the journal items (account.move.line) corresponding to the price difference
         lines for vendor bills. It only concerns the quantities that have been delivered before the bill
        Example:
        Buy a product having a cost of 9 and a supplier price of 10 and being a storable product and having a perpetual
        valuation in FIFO. Deliver the product and then post the bill. The vendor bill's journal entries looks like:
        Account                                     | Debit | Credit
        ---------------------------------------------------------------
        101120 Stock Interim Account (Received)     | 10.0  |
        ---------------------------------------------------------------
        101100 Account Payable                      |       | 10.0
        ---------------------------------------------------------------
        This method computes values used to make two additional journal items:
        ---------------------------------------------------------------
        101120 Stock Interim Account (Received)     |       | 1.0
        ---------------------------------------------------------------
        xxxxxx Expenses                             | 1.0   |
        ---------------------------------------------------------------
        :return: A list of Python dictionary to be passed to env['account.move.line'].create.
        '''
        lines_vals_list = []
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')

        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund', 'in_receipt') or not move.company_id.anglo_saxon_accounting:
                continue

            move = move.with_company(move.company_id)
            for line in move.invoice_line_ids:
                # Filter out lines being not eligible for price difference.
                # Moreover, this function is used for standard cost method only.
                if line.product_id.type != 'product' or line.product_id.valuation != 'real_time' or line.product_id.cost_method != 'standard':
                    continue

                # Retrieve accounts needed to generate the price difference.
                debit_expense_account = line._get_price_diff_account()
                if not debit_expense_account:
                    continue
                # Retrieve stock valuation moves.
                valuation_stock_moves = self.env['stock.move'].search([
                    ('purchase_line_id', '=', line.purchase_line_id.id),
                    ('state', '=', 'done'),
                    ('product_qty', '!=', 0.0),
                ]) if line.purchase_line_id else self.env['stock.move']

                if line.product_id.cost_method != 'standard' and line.purchase_line_id:
                    if move.move_type == 'in_refund':
                        valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_out())
                    else:
                        valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_in())

                    if not valuation_stock_moves:
                        continue

                    valuation_price_unit_total, valuation_total_qty = valuation_stock_moves._get_valuation_price_and_qty(line, move.currency_id)
                    valuation_price_unit = valuation_price_unit_total / valuation_total_qty
                    valuation_price_unit = line.product_id.uom_id._compute_price(valuation_price_unit, line.product_uom_id)
                else:
                    # Valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
                    price_unit = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id)
                    price_unit = -price_unit if line.move_id.move_type == 'in_refund' else price_unit
                    valuation_date = valuation_stock_moves and max(valuation_stock_moves.mapped('date')) or move.date
                    valuation_price_unit = line.company_currency_id._convert(
                        price_unit, move.currency_id,
                        move.company_id, valuation_date, round=False
                    )


                price_unit = line._get_gross_unit_price()

                price_unit_val_dif = price_unit - valuation_price_unit
                # If there are some valued moves, we only consider their quantity already used
                if line.product_id.cost_method == 'standard':
                    relevant_qty = line.quantity
                else:
                    relevant_qty = line._get_out_and_not_invoiced_qty(valuation_stock_moves)
                price_subtotal = relevant_qty * price_unit_val_dif

                # We consider there is a price difference if the subtotal is not zero. In case a
                # discount has been applied, we can't round the price unit anymore, and hence we
                # can't compare them.
                if (
                    not move.currency_id.is_zero(price_subtotal)
                    and float_compare(line["price_unit"], line.price_unit, precision_digits=price_unit_prec) == 0
                ):

                    # Add price difference account line.
                    vals = {
                        'name': line.name[:64],
                        'move_id': move.id,
                        'partner_id': line.partner_id.id or move.commercial_partner_id.id,
                        'currency_id': line.currency_id.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'quantity': relevant_qty,
                        'price_unit': price_unit_val_dif,
                        'price_subtotal': relevant_qty * price_unit_val_dif,
                        'amount_currency': relevant_qty * price_unit_val_dif * line.move_id.direction_sign,
                        'balance': line.currency_id._convert(
                            relevant_qty * price_unit_val_dif * line.move_id.direction_sign,
                            line.company_currency_id,
                            line.company_id, fields.Date.today(),
                        ),
                        'account_id': debit_expense_account.id,
                        'analytic_distribution': line.analytic_distribution,
                        'display_type': 'cogs',
                    }
                    lines_vals_list.append(vals)

                    # Correct the amount of the current line.
                    vals = {
                        'name': line.name[:64],
                        'move_id': move.id,
                        'partner_id': line.partner_id.id or move.commercial_partner_id.id,
                        'currency_id': line.currency_id.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'quantity': relevant_qty,
                        'price_unit': -price_unit_val_dif,
                        'price_subtotal': relevant_qty * -price_unit_val_dif,
                        'amount_currency': relevant_qty * -price_unit_val_dif * line.move_id.direction_sign,
                        'balance': line.currency_id._convert(
                            relevant_qty * -price_unit_val_dif * line.move_id.direction_sign,
                            line.company_currency_id,
                            line.company_id, fields.Date.today(),
                        ),
                        'account_id': line.account_id.id,
                        'analytic_distribution': line.analytic_distribution,
                        'display_type': 'cogs',
                    }
                    lines_vals_list.append(vals)
        return lines_vals_list

    def _post(self, soft=True):
        if not self._context.get('move_reverse_cancel'):
            self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_in_lines_vals())

        # Create correction layer and impact accounts if invoice price is different
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        valued_lines = self.env['account.move.line'].sudo()
        for invoice in self:
            if invoice.sudo().stock_valuation_layer_ids:
                continue
            if invoice.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                valued_lines |= invoice.invoice_line_ids.filtered(
                    lambda l: l.product_id and l.product_id.cost_method != 'standard')
        if valued_lines:
            svls, _amls = valued_lines._apply_price_difference()
            stock_valuation_layers |= svls

        for (product, company), dummy in groupby(stock_valuation_layers, key=lambda svl: (svl.product_id, svl.company_id)):
            product = product.with_company(company.id)
            if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})

        if stock_valuation_layers:
            stock_valuation_layers._validate_accounting_entries()

        posted = super()._post(soft)
        # The invoice reference is set during the super call
        for layer in stock_valuation_layers:
            description = f"{layer.account_move_line_id.move_id.display_name} - {layer.product_id.display_name}"
            layer.description = description
            if layer.product_id.valuation != 'real_time':
                continue
            layer.account_move_id.ref = description
            layer.account_move_id.line_ids.write({'name': description})

        return posted

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'in_invoice'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'supplier')
        for invoice in self.filtered(lambda x: x.move_type == 'in_refund'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'supplier')
        return rslt
