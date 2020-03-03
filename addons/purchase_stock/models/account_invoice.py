# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

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

        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund', 'in_receipt') or not move.company_id.anglo_saxon_accounting:
                continue

            move = move.with_company(move.company_id)
            for line in move.invoice_line_ids.filtered(lambda line: line.product_id.type == 'product' and line.product_id.valuation == 'real_time'):

                # Filter out lines being not eligible for price difference.
                if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                    continue

                if line.product_id.cost_method != 'standard' and line.purchase_line_id:
                    po_currency = line.purchase_line_id.currency_id
                    po_company = line.purchase_line_id.company_id

                    # Retrieve stock valuation moves.
                    valuation_stock_moves = self.env['stock.move'].search([
                        ('purchase_line_id', '=', line.purchase_line_id.id),
                        ('state', '=', 'done'),
                        ('product_qty', '!=', 0.0),
                    ])
                    if move.move_type == 'in_refund':
                        valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_out())
                    else:
                        valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_in())

                    if valuation_stock_moves:
                        valuation_price_unit_total = 0
                        valuation_total_qty = 0
                        for val_stock_move in valuation_stock_moves:
                            # In case val_stock_move is a return move, its valuation entries have been made with the
                            # currency rate corresponding to the original stock move
                            valuation_date = val_stock_move.origin_returned_move_id.date or val_stock_move.date
                            svl = val_stock_move.mapped('stock_valuation_layer_ids').filtered(lambda l: l.quantity)
                            layers_qty = sum(svl.mapped('quantity'))
                            layers_values = sum(svl.mapped('value'))
                            valuation_price_unit_total += line.company_currency_id._convert(
                                layers_values, move.currency_id,
                                move.company_id, valuation_date, round=False,
                            )
                            valuation_total_qty += layers_qty
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

                invoice_cur_prec = move.currency_id.decimal_places

                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                if line.tax_ids:
                    price_unit = line.tax_ids.compute_all(
                        price_unit, currency=move.currency_id, quantity=1.0, is_refund=move.move_type == 'in_refund')['total_excluded']

                if line.quantity and float_compare(valuation_price_unit, price_unit, precision_digits=invoice_cur_prec) != 0 \
                        and float_compare(line['price_unit'], line.price_unit, precision_digits=invoice_cur_prec) == 0:

                    price_unit_val_dif = price_unit - valuation_price_unit

                    if move.currency_id.compare_amounts(price_unit, valuation_price_unit) != 0:
                        accounts = line.product_id.product_tmpl_id.get_product_accounts()
                        stock_valuation_account = accounts.get('stock_valuation')

                        # Retrieve stock valuation moves.
                        valuation_stock_moves = self.env['stock.move'].search([
                            ('purchase_line_id', '=', line.purchase_line_id.id),
                            ('product_qty', '!=', 0.0),
                        ])
                        if move.move_type == 'in_refund':
                            valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_out())
                        else:
                            valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_in())
                        valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move.state == 'done')

                        if valuation_stock_moves.stock_valuation_layer_ids:
                            qty_invoiced = line.purchase_line_id.qty_invoiced
                            qty_received = line.purchase_line_id.qty_received
                            qty_to_diff = qty_received - (qty_invoiced - line.quantity)
                            if qty_to_diff <= 0:
                                continue
                            product = line.product_id
                            linked_layer = valuation_stock_moves.stock_valuation_layer_ids[-1]
                            svl_vals = []
                            price_unit_val_dif = line.price_unit - linked_layer.unit_cost
                            price_subtotal = qty_to_diff * price_unit_val_dif
                            if price_unit_val_dif == 0:
                                continue

                            # Create a new stock valuation layer for the price difference.
                            svl_vals.append({
                                'company_id': line.company_id.id,
                                'product_id': product.id,
                                'description': _('Price difference between %s and %s') % (move.purchase_id.name, move._get_next_sequence()),
                                'value': price_subtotal,
                                'quantity': 0,
                                'account_move_id': move.id,
                                'stock_valuation_layer_id': linked_layer.id
                            })
                            # Update the standard price if product cost method is AVCO.
                            if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                                product.with_company(self.company_id).sudo().with_context(disable_auto_svl=True).standard_price += price_unit_val_dif / product.quantity_svl

                            # If the product already left the stock, create a
                            # negative counter part for the stock valuation layer.
                            product_already_out = float_is_zero(linked_layer.remaining_qty, precision_rounding=product.uom_id.rounding)
                            if product_already_out:
                                svl_vals[0]['quantity'] = 1
                                svl_out_vals = dict(svl_vals[0], **{
                                    'quantity': -1,
                                    'description': _('Adjustment of price difference between %s and %s as the product is already out') % (move.purchase_id.name, move._get_next_sequence()),
                                    'value': -price_subtotal,
                                })
                                svl_vals.append(svl_out_vals)
                            else:
                                linked_layer.remaining_value += price_subtotal

                            self.env['stock.valuation.layer'].sudo().create(svl_vals)

                            # Add an account line for the price difference.
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

                            # Creates the journal entries for the output.
                            if product_already_out:
                                # Add also an account line for the price difference for the output side.
                                common_vals['name'] = common_vals['name'] + (_(": %s already out") % line.quantity)
                                vals = dict(common_vals, **{
                                    'price_unit': -price_unit_val_dif,
                                    'price_subtotal': -price_subtotal,
                                    'account_id': stock_valuation_account.id,
                                })
                                vals.update(line._get_fields_onchange_subtotal(price_subtotal=vals['price_subtotal']))
                                lines_vals_list.append(vals)

                                # Retrieve accounts needed.
                                accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
                                debit_interim_account = accounts['stock_output']
                                credit_expense_account = accounts['expense']

                                vals = dict(common_vals, **{
                                    'price_unit': price_unit_val_dif,
                                    'price_subtotal': price_subtotal,
                                    'account_id': debit_interim_account.id,
                                })
                                vals.update(line._get_fields_onchange_subtotal(price_subtotal=vals['price_subtotal']))
                                lines_vals_list.append(vals)

                                # Add interim account line.
                                vals = {
                                    'name': line.name[:64] + (_(": %s already out") % line.quantity),
                                    'move_id': move.id,
                                    'product_id': line.product_id.id,
                                    'product_uom_id': line.product_uom_id.id,
                                    'quantity': line.quantity,
                                    'price_unit': -price_unit_val_dif,
                                    'price_subtotal': -price_subtotal,
                                    'account_id': debit_interim_account.id,
                                    'exclude_from_invoice_tab': True,
                                    'is_anglo_saxon_line': True,
                                }
                                vals.update(line._get_fields_onchange_subtotal(price_subtotal=vals['price_subtotal']))
                                lines_vals_list.append(vals)

                                # Add the price diff. in the expense account line.
                                vals = {
                                    'name': line.name[:64] + (_(": %s already out") % line.quantity),
                                    'move_id': move.id,
                                    'product_id': line.product_id.id,
                                    'product_uom_id': line.product_uom_id.id,
                                    'quantity': line.quantity,
                                    'price_unit': price_unit_val_dif,
                                    'price_subtotal': price_subtotal,
                                    'account_id': credit_expense_account.id,
                                    'analytic_account_id': line.analytic_account_id.id,
                                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                                    'exclude_from_invoice_tab': True,
                                    'is_anglo_saxon_line': True,
                                }
                                vals.update(line._get_fields_onchange_subtotal(price_subtotal=vals['price_subtotal']))
                                lines_vals_list.append(vals)

        return lines_vals_list

    def _post(self, soft=True):
        # OVERRIDE
        # Create additional price difference lines for vendor bills.
        if self._context.get('move_reverse_cancel'):
            return super()._post(soft)
        self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_in_lines_vals())
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
