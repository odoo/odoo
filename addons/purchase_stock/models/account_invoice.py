# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools import float_compare, float_is_zero
from odoo.tools.misc import unique


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
        101120 Stock Account                        | 10.0  |
        ---------------------------------------------------------------
        101100 Account Payable                      |       | 10.0
        ---------------------------------------------------------------
        This method computes values used to make two additional journal items:
        ---------------------------------------------------------------
        101120 Stock Account                        |       | 1.0
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
                if not line._eligible_for_stock_account() or line.product_id.cost_method != 'standard':
                    continue

                # Retrieve accounts needed to generate the price difference.

                debit_pdiff_account = False
                if line.product_id.cost_method == 'standard':
                    debit_pdiff_account = line.product_id.categ_id.property_price_difference_account_id
                    debit_pdiff_account = move.fiscal_position_id.map_account(debit_pdiff_account)
                else:
                    debit_pdiff_account = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)['expense']
                if not debit_pdiff_account:
                    continue

                price_unit_val_dif, relevant_qty = line._get_price_unit_val_dif_and_relevant_qty()
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
                        'account_id': debit_pdiff_account.id,
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

    def button_draft(self):
        return super().button_draft()

    def _post(self, soft=True):
        if not self.env.context.get('move_reverse_cancel'):
            self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_in_lines_vals())

        return super()._post(soft)

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super()._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'in_invoice'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'supplier')
        for invoice in self.filtered(lambda x: x.move_type == 'in_refund'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'supplier')
        return rslt

    @api.depends('purchase_id')
    def _compute_incoterm_location(self):
        super()._compute_incoterm_location()
        for move in self:
            purchase_locations = move.line_ids.purchase_line_id.order_id.mapped('incoterm_location')
            incoterm_res = next((incoterm for incoterm in purchase_locations if incoterm), False)
            # if multiple purchase order we take an incoterm that is not false
            if incoterm_res:
                move.incoterm_location = incoterm_res
