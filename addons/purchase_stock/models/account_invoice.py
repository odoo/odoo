# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
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
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')

        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund', 'in_receipt') or not move.company_id.anglo_saxon_accounting:
                continue

            move = move.with_company(move.company_id)
            for line in move.invoice_line_ids:
                # Filter out lines being not eligible for price difference.
                if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                    continue

                # Retrieve accounts needed to generate the price difference.
                debit_pdiff_account = line.product_id.property_account_creditor_price_difference \
                                or line.product_id.categ_id.property_account_creditor_price_difference_categ
                debit_pdiff_account = move.fiscal_position_id.map_account(debit_pdiff_account)
                if not debit_pdiff_account:
                    continue
                # Retrieve stock valuation moves.
                valuation_stock_moves = self.env['stock.move'].search([
                    ('purchase_line_id', '=', line.purchase_line_id.id),
                    ('state', '=', 'done'),
                    ('product_qty', '!=', 0.0),
                ]) if line.purchase_line_id else self.env['stock.move']
                if move.move_type == 'in_refund':
                    valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_out())
                else:
                    valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_in())

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
                    valuation_date = valuation_stock_moves and max(valuation_stock_moves.mapped('date')) or move.date
                    valuation_price_unit = line.company_currency_id._convert(
                        price_unit, move.currency_id,
                        move.company_id, valuation_date, round=False
                    )


                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                if line.tax_ids:
                    # We do not want to round the price unit since :
                    # - It does not follow the currency precision
                    # - It may include a discount
                    # Since compute_all still rounds the total, we use an ugly workaround:
                    # shift the decimal part using a fixed quantity to avoid rounding issues
                    prec = 1e+6
                    price_unit *= prec
                    price_unit = line.tax_ids.with_context(round=False, force_sign=move._get_tax_force_sign()).compute_all(
                        price_unit, currency=move.currency_id, quantity=1.0, is_refund=move.move_type == 'in_refund')['total_excluded']
                    price_unit /= prec

                price_unit_val_dif = price_unit - valuation_price_unit
                price_subtotal = line.quantity * price_unit_val_dif

                # We consider there is a price difference if:
                # - price unit is not zero with respect to product price decimal precision.
                # - subtotal is not zero with respect to move currency precision.
                # - no discount was applied, as we can't round the price unit anymore
                if (
                    not move.currency_id.is_zero(price_subtotal)
                    and not float_is_zero(price_unit_val_dif, precision_digits=price_unit_prec)
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
                        'quantity': line.quantity,
                        'price_unit': price_unit_val_dif,
                        'price_subtotal': line.quantity * price_unit_val_dif,
                        'account_id': debit_pdiff_account.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                        'exclude_from_invoice_tab': True,
                        'is_anglo_saxon_line': True,
                    }
                    vals.update(line._get_fields_onchange_subtotal(price_subtotal=vals['price_subtotal']))
                    lines_vals_list.append(vals)

                    # Correct the amount of the current line.
                    vals = {
                        'name': line.name[:64],
                        'move_id': move.id,
                        'partner_id': line.partner_id.id or move.commercial_partner_id.id,
                        'currency_id': line.currency_id.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'quantity': line.quantity,
                        'price_unit': -price_unit_val_dif,
                        'price_subtotal': line.quantity * -price_unit_val_dif,
                        'account_id': line.account_id.id,
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
