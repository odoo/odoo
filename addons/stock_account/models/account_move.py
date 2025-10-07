# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_id = fields.Many2one('stock.move', string='Stock Move', index='btree_not_null')
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'account_move_id', string='Stock Valuation Layer')

    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.sudo().line_ids.stock_valuation_layer_ids:
                move.show_reset_to_draft_button = False

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    def _get_lines_onchange_currency(self):
        # OVERRIDE
        return self.line_ids.filtered(lambda l: l.display_type != 'cogs')

    def copy_data(self, default=None):
        # OVERRIDE
        # Don't keep anglo-saxon lines when copying a journal entry.
        res = super().copy_data(default=default)

        if not self._context.get('move_reverse_cancel'):
            for copy_vals in res:
                if 'line_ids' in copy_vals:
                    copy_vals['line_ids'] = [line_vals for line_vals in copy_vals['line_ids']
                                             if line_vals[0] != 0 or line_vals[2].get('display_type') != 'cogs']

        return res

    def _post(self, soft=True):
        # OVERRIDE

        # Don't change anything on moves used to cancel another ones.
        if self._context.get('move_reverse_cancel'):
            return super()._post(soft)

        # Create additional COGS lines for customer invoices.
        self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_out_lines_vals())

        # Post entries.
        posted = super()._post(soft)

        # Reconcile COGS lines in case of anglo-saxon accounting with perpetual valuation.
        if not self.env.context.get('skip_cogs_reconciliation'):
            posted._stock_account_anglo_saxon_reconcile_valuation()
        return posted

    def button_draft(self):
        res = super(AccountMove, self).button_draft()

        # Unlink the COGS lines generated during the 'post' method.
        self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()
        return res

    def button_cancel(self):
        # OVERRIDE
        res = super(AccountMove, self).button_cancel()

        # Unlink the COGS lines generated during the 'post' method.
        # In most cases it shouldn't be necessary since they should be unlinked with 'button_draft'.
        # However, since it can be called in RPC, better be safe.
        self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()
        return res

    # -------------------------------------------------------------------------
    # COGS METHODS
    # -------------------------------------------------------------------------

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        ''' Prepare values used to create the journal items (account.move.line) corresponding to the Cost of Good Sold
        lines (COGS) for customer invoices.

        Example:

        Buy a product having a cost of 9 being a storable product and having a perpetual valuation in FIFO.
        Sell this product at a price of 10. The customer invoice's journal entries looks like:

        Account                                     | Debit | Credit
        ---------------------------------------------------------------
        200000 Product Sales                        |       | 10.0
        ---------------------------------------------------------------
        101200 Account Receivable                   | 10.0  |
        ---------------------------------------------------------------

        This method computes values used to make two additional journal items:

        ---------------------------------------------------------------
        220000 Expenses                             | 9.0   |
        ---------------------------------------------------------------
        101130 Stock Interim Account (Delivered)    |       | 9.0
        ---------------------------------------------------------------

        Note: COGS are only generated for customer invoices except refund made to cancel an invoice.

        :return: A list of Python dictionary to be passed to env['account.move.line'].create.
        '''
        lines_vals_list = []
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        for move in self:
            # Make the loop multi-company safe when accessing models like product.product
            move = move.with_company(move.company_id)

            if not move.is_sale_document(include_receipts=True) or not move.company_id.anglo_saxon_accounting:
                continue

            anglo_saxon_price_ctx = move._get_anglo_saxon_price_ctx()

            for line in move.invoice_line_ids:

                # Filter out lines being not eligible for COGS.
                if not line._eligible_for_cogs():
                    continue

                # Retrieve accounts needed to generate the COGS.
                accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
                debit_interim_account = accounts['stock_output']
                credit_expense_account = accounts['expense'] or move.journal_id.default_account_id
                if not debit_interim_account or not credit_expense_account:
                    continue

                # Compute accounting fields.
                sign = -1 if move.move_type == 'out_refund' else 1
                price_unit = line.with_context(anglo_saxon_price_ctx)._stock_account_get_anglo_saxon_price_unit()
                amount_currency = sign * line.quantity * price_unit

                if move.currency_id.is_zero(amount_currency) or float_is_zero(price_unit, precision_digits=price_unit_prec):
                    continue

                # Add interim account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'partner_id': move.commercial_partner_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': price_unit,
                    'amount_currency': -amount_currency,
                    'account_id': debit_interim_account.id,
                    'display_type': 'cogs',
                    'tax_ids': [],
                })

                # Add expense account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'partner_id': move.commercial_partner_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': -price_unit,
                    'amount_currency': amount_currency,
                    'account_id': credit_expense_account.id,
                    'analytic_distribution': line.analytic_distribution,
                    'display_type': 'cogs',
                    'tax_ids': [],
                })
        return lines_vals_list

    def _get_anglo_saxon_price_ctx(self):
        """ To be overriden in modules overriding _stock_account_get_anglo_saxon_price_unit
        to optimize computations that only depend on account.move and not account.move.line
        """
        return self.env.context

    def _stock_account_get_last_step_stock_moves(self):
        """ To be overridden for customer invoices and vendor bills in order to
        return the stock moves related to the invoices in self.
        """
        return self.env['stock.move']

    def _stock_account_anglo_saxon_reconcile_valuation(self, product=False):
        """ Reconciles the entries made in the interim accounts in anglosaxon accounting,
        reconciling stock valuation move lines with the invoice's.
        """
        for move in self:
            if not move.is_invoice():
                continue
            if not move.company_id.anglo_saxon_accounting:
                continue

            stock_moves = move._stock_account_get_last_step_stock_moves()
            # In case we return a return, we have to provide the related AMLs so all can be reconciled
            stock_moves |= stock_moves.origin_returned_move_id

            if not stock_moves:
                continue

            products = product or move.mapped('invoice_line_ids.product_id')
            for prod in products:
                if prod.valuation != 'real_time':
                    continue

                # We first get the invoices move lines (taking the invoice and the previous ones into account)...
                product_accounts = prod.product_tmpl_id._get_product_accounts()
                if move.is_sale_document():
                    product_interim_account = product_accounts['stock_output']
                else:
                    product_interim_account = product_accounts['stock_input']

                if product_interim_account.reconcile:
                    # Search for anglo-saxon lines linked to the product in the journal entry.
                    product_account_moves = move.line_ids.filtered(
                        lambda line: line.product_id == prod and line.account_id == product_interim_account and not line.reconciled)

                    # Search for anglo-saxon lines linked to the product in the stock moves.
                    product_stock_moves = stock_moves._get_all_related_sm(prod)
                    product_account_moves |= product_stock_moves._get_all_related_aml().filtered(
                        lambda line: line.account_id == product_interim_account and not line.reconciled and line.move_id.state == "posted"
                    )

                    correction_amls = product_account_moves.filtered(
                        lambda aml: aml.move_id.sudo().stock_valuation_layer_ids.stock_valuation_layer_id or (aml.display_type == 'cogs' and not aml.quantity)
                    )
                    invoice_aml = product_account_moves.filtered(lambda aml: aml not in correction_amls and aml.move_id == move)
                    stock_aml = product_account_moves - correction_amls - invoice_aml
                    # Reconcile:
                    # In case there is a move with correcting lines that has not been posted
                    # (e.g., it's dated for some time in the future) we should defer any
                    # reconciliation with exchange difference.
                    if correction_amls or 'draft' in move.line_ids.sudo().stock_valuation_layer_ids.account_move_id.mapped('state'):
                        if sum(correction_amls.mapped('balance')) > 0:
                            product_account_moves.with_context(no_exchange_difference=True).reconcile()
                        else:
                            (invoice_aml | correction_amls).with_context(no_exchange_difference=True).reconcile()
                            (invoice_aml.filtered(lambda aml: not aml.reconciled) | stock_aml).with_context(no_exchange_difference=True).reconcile()
                    else:
                        product_account_moves.reconcile()

    def _get_invoiced_lot_values(self):
        return []


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'account_move_line_id', string='Stock Valuation Layer')

    def _compute_account_id(self):
        super()._compute_account_id()
        input_lines = self.filtered(lambda line: (
            line._can_use_stock_accounts()
            and line.move_id.company_id.anglo_saxon_accounting
            and line.move_id.is_purchase_document()
        ))
        for line in input_lines:
            line = line.with_company(line.move_id.journal_id.company_id)
            fiscal_position = line.move_id.fiscal_position_id
            accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if accounts['stock_input']:
                line.account_id = accounts['stock_input']

    def _eligible_for_cogs(self):
        self.ensure_one()
        return self.product_id.type == 'product' and self.product_id.valuation == 'real_time'

    def _get_gross_unit_price(self):
        if float_is_zero(self.quantity, precision_rounding=self.product_uom_id.rounding):
            return self.price_unit

        price_unit = self.price_subtotal / self.quantity
        return -price_unit if self.move_id.move_type == 'in_refund' else price_unit

    def _get_stock_valuation_layers(self, move):
        valued_moves = self._get_valued_in_moves()
        if move.move_type == 'in_refund':
            valued_moves = valued_moves.filtered(lambda stock_move: stock_move._is_out())
        else:
            valued_moves = valued_moves.filtered(lambda stock_move: stock_move._is_in())
        return valued_moves.stock_valuation_layer_ids

    def _get_valued_in_moves(self):
        return self.env['stock.move']

    def _can_use_stock_accounts(self):
        return self.product_id.type == 'product' and self.product_id.categ_id.property_valuation == 'real_time'

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        original_line = self.move_id.reversed_entry_id.line_ids.filtered(
            lambda l: l.display_type == 'cogs' and l.product_id == self.product_id and
            l.product_uom_id == self.product_uom_id and l.price_unit >= 0)
        original_line = original_line and original_line[0]
        return original_line.price_unit if original_line \
            else self.product_id.with_company(self.company_id)._stock_account_get_anglo_saxon_price_unit(uom=self.product_uom_id)

    @api.onchange('product_id')
    def _inverse_product_id(self):
        super(AccountMoveLine, self.filtered(lambda l: l.display_type != 'cogs'))._inverse_product_id()

    def _deduce_anglo_saxon_unit_price(self, account_moves, stock_moves):
        self.ensure_one()

        move_is_downpayment = self.env.context.get("move_is_downpayment")
        if move_is_downpayment is None:
            move_is_downpayment = self.move_id.invoice_line_ids.filtered(
                lambda line: any(line.sale_line_ids.mapped("is_downpayment"))
            )

        is_line_reversing = False
        if self.move_id.move_type == 'out_refund' and not move_is_downpayment:
            is_line_reversing = True
        qty_to_invoice = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
        if self.move_id.move_type == 'out_refund' and move_is_downpayment:
            qty_to_invoice = -qty_to_invoice
        account_moves = account_moves.filtered(lambda m: m.state == 'posted' and bool(m.reversed_entry_id) == is_line_reversing)

        posted_cogs = self.env['account.move.line'].search([
            ('move_id', 'in', account_moves.ids),
            ('display_type', '=', 'cogs'),
            ('product_id', '=', self.product_id.id),
            ('balance', '>', 0),
        ])
        qty_invoiced = 0
        product_uom = self.product_id.uom_id
        for line in posted_cogs:
            if float_compare(line.quantity, 0, precision_rounding=product_uom.rounding) and line.move_id.move_type == 'out_refund' and any(line.move_id.invoice_line_ids.sale_line_ids.mapped('is_downpayment')):
                qty_invoiced += line.product_uom_id._compute_quantity(abs(line.quantity), line.product_id.uom_id)
            else:
                qty_invoiced += line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
        value_invoiced = sum(posted_cogs.mapped('balance'))
        reversal_moves = self.env['account.move']._search([('reversed_entry_id', 'in', posted_cogs.move_id.ids)])
        reversal_cogs = self.env['account.move.line'].search([
            ('move_id', 'in', reversal_moves),
            ('display_type', '=', 'cogs'),
            ('product_id', '=', self.product_id.id),
            ('balance', '>', 0)
        ])
        for line in reversal_cogs:
            if float_compare(line.quantity, 0, precision_rounding=product_uom.rounding) and line.move_id.move_type == 'out_refund' and any(line.move_id.invoice_line_ids.sale_line_ids.mapped('is_downpayment')):
                qty_invoiced -= line.product_uom_id._compute_quantity(abs(line.quantity), line.product_id.uom_id)
            else:
                qty_invoiced -= line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
        value_invoiced -= sum(reversal_cogs.mapped('balance'))

        product = self.product_id.with_company(self.company_id).with_context(value_invoiced=value_invoiced)
        average_price_unit = product._compute_average_price(qty_invoiced, qty_to_invoice, stock_moves, is_returned=is_line_reversing)
        price_unit = self.product_id.uom_id.with_company(self.company_id)._compute_price(average_price_unit, self.product_uom_id)

        return price_unit

    def create(self, vals_list):
        if self._context.get('is_price_change'):
            vals_list = [val for val in vals_list if val.get('display_type') != 'tax']
        return super().create(vals_list)
