# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _retrieve_stock_valuation_moves(self, line):
        self.ensure_one()
        valuation_stock_moves = self.env['stock.move'].search([
            ('purchase_line_id', '=', line.purchase_line_id.id),
            ('state', '=', 'done'),
            ('product_qty', '!=', 0.0),
        ])
        if self.move_type == 'in_refund':
            valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_out())
        else:
            valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_in())
        return valuation_stock_moves

    def _skip_move_for_price_diff(self):
        self.ensure_one()
        return self.move_type not in ('in_invoice', 'in_refund', 'in_receipt') or not self.company_id.anglo_saxon_accounting

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        ''' Prepare values used to create the journal items (account.move.line) corresponding to the price difference
         lines for vendor bills.

        Example:

        Buy a product having a cost of 9 and a supplier price of 10 and being a storable product and having a perpetual
        valuation in FIFO. The vendor bill's journal entries looks like:

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
        xxxxxx Price Difference Account             | 1.0   |
        ---------------------------------------------------------------

        :return: A list of Python dictionary to be passed to env['account.move.line'].create.
        '''
        lines_vals_list = []
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')

        for move in self:
            if move._skip_move_for_price_diff():
                continue

            move = move.with_company(move.company_id)
            for line in move.invoice_line_ids:
                if line._is_not_eligible_for_price_difference():
                    continue

                # Retrieve stock valuation moves.
                valuation_stock_moves = move._retrieve_stock_valuation_moves(line)

                if line.product_id.cost_method != 'standard' and line.purchase_line_id:
                    po_currency = line.purchase_line_id.currency_id
                    po_company = line.purchase_line_id.company_id

                    if valuation_stock_moves:
                        valuation_price_unit_total, valuation_total_qty = valuation_stock_moves._get_valuation_price_and_qty(line, move.currency_id)
                        valuation_price_unit = valuation_price_unit_total / valuation_total_qty
                        valuation_price_unit = line.product_id.uom_id._compute_price(valuation_price_unit, line.product_uom_id)

                    elif line.product_id.cost_method == 'fifo':
                        # In this condition, we have a real price-valuated product which has not yet been received
                        valuation_price_unit = po_currency._convert(
                            line.purchase_line_id.price_unit, move.currency_id,
                            po_company, move.date, round=False,
                        )
                    else:
                        # For average/fifo/lifo costing method, fetch real cost price from incoming moves.
                        price_unit = line.purchase_line_id.product_uom._compute_price(line.purchase_line_id.price_unit, line.product_uom_id)
                        valuation_price_unit = po_currency._convert(
                            price_unit, move.currency_id,
                            po_company, move.date, round=False
                        )
                else:
                    # Valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
                    price_unit = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id)
                    valuation_price_unit = line.company_currency_id._convert(
                        price_unit, move.currency_id,
                        move.company_id, fields.Date.today(), round=False
                    )

                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                if line.tax_ids:
                    if line.discount and line.quantity:
                        # We do not want to round the price unit since :
                        # - It does not follow the currency precision
                        # - It may include a discount
                        # Since compute_all still rounds the total, we use an ugly workaround:
                        # multiply then divide the price unit.
                        price_unit *= line.quantity
                        price_unit = line.tax_ids.with_context(round=False, force_sign=move._get_tax_force_sign()).compute_all(
                            price_unit, currency=move.currency_id, quantity=1.0, is_refund=move.move_type == 'in_refund')['total_excluded']
                        price_unit /= line.quantity
                    else:
                        price_unit = line.tax_ids.compute_all(
                            price_unit, currency=move.currency_id, quantity=1.0, is_refund=move.move_type == 'in_refund')['total_excluded']

                price_unit_val_dif = price_unit - valuation_price_unit
                price_subtotal = line.quantity * price_unit_val_dif

                # We consider there is a price difference if the subtotal is not zero. In case a
                # discount has been applied, we can't round the price unit anymore, and hence we
                # can't compare them.
                if (
                    not move.currency_id.is_zero(price_subtotal)
                    and float_compare(line["price_unit"], line.price_unit, precision_digits=price_unit_prec) == 0
                ):
                    accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
                    stock_valuation_account = accounts.get('stock_valuation')

                    if valuation_stock_moves.stock_valuation_layer_ids:
                        qty_invoiced = line.purchase_line_id.qty_invoiced
                        qty_received = line.purchase_line_id.qty_received
                        qty_to_diff = qty_received - (qty_invoiced - line.quantity)
                        if qty_to_diff <= 0:
                            continue
                        product = line.product_id
                        linked_layers = valuation_stock_moves.stock_valuation_layer_ids
                        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        price_unit_val_dif = price_unit - sum(linked_layers.mapped('unit_cost'))
                        price_subtotal = qty_to_diff * price_unit_val_dif
                        if price_unit_val_dif == 0:
                            continue

                        # Adds an account line for the price difference.
                        common_vals = {
                            'name': line.name[:64],
                            'move_id': move.id,
                            'currency_id': line.currency_id.id,
                            'product_id': product.id,
                            'product_uom_id': line.product_uom_id.id,
                            'quantity': line.quantity,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                            'exclude_from_invoice_tab': True,
                            'is_anglo_saxon_line': True,
                        }
                        vals = dict(common_vals, **{
                            'price_unit': price_unit_val_dif,
                            'price_subtotal': price_subtotal,
                            'account_id': stock_valuation_account.id,
                        })
                        vals.update(line._get_fields_onchange_subtotal(price_subtotal=vals['price_subtotal']))
                        lines_vals_list.append(vals)

                        # Correct the amount of the current line.
                        vals = dict(common_vals, **{
                            'price_unit': -price_unit_val_dif,
                            'price_subtotal': -price_subtotal,
                            'account_id': line.account_id.id,
                        })
                        vals.update(line._get_fields_onchange_subtotal(price_subtotal=vals['price_subtotal']))
                        lines_vals_list.append(vals)

        return lines_vals_list

    def _post(self, soft=True):
        # OVERRIDE
        # Create additional price difference lines for vendor bills.
        if self._context.get('move_reverse_cancel'):
            return super()._post(soft)
        account_move_line_vals = self._stock_account_prepare_anglo_saxon_in_lines_vals()
        stock_valuation_layer_vals = self.invoice_line_ids._get_price_difference_svl_values()
        self.env['account.move.line'].create(account_move_line_vals)
        self.env['stock.valuation.layer'].create(stock_valuation_layer_vals)
        self.invoice_line_ids._update_qty_waiting_for_receipt()
        return super()._post(soft)

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'in_invoice'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'supplier')
        for invoice in self.filtered(lambda x: x.move_type == 'in_refund'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'supplier')
        return rslt
