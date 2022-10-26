# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.tools.misc import groupby


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_id = fields.Many2one('stock.move', string='Stock Move', index='btree_not_null')
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'account_move_id', string='Stock Valuation Layer')

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

        # Create correction layer if invoice price is different
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        valued_lines = self.env['account.move.line'].sudo()
        for invoice in self:
            if invoice.sudo().stock_valuation_layer_ids:
                continue
            if invoice.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                valued_lines |= invoice.invoice_line_ids.filtered(
                    lambda l: l.product_id and l.product_id.cost_method != 'standard')
        if valued_lines:
            stock_valuation_layers |= valued_lines._create_in_invoice_svl()

        for (product, company), dummy in groupby(stock_valuation_layers, key=lambda svl: (svl.product_id, svl.company_id)):
            product = product.with_company(company.id)
            if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})

        if stock_valuation_layers:
            stock_valuation_layers._validate_accounting_entries()

        # Create additional COGS lines for customer invoices.
        self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_out_lines_vals())

        # Post entries.
        posted = super()._post(soft)

        # The invoice reference is set during the super call
        for layer in stock_valuation_layers:
            description = f"{layer.account_move_line_id.move_id.display_name} - {layer.product_id.display_name}"
            layer.description = description
            layer.account_move_id.ref = description
            layer.account_move_id.line_ids.write({'name': description})

        # Reconcile COGS lines in case of anglo-saxon accounting with perpetual valuation.
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
        for move in self:
            # Make the loop multi-company safe when accessing models like product.product
            move = move.with_company(move.company_id)

            if not move.is_sale_document(include_receipts=True) or not move.company_id.anglo_saxon_accounting:
                continue

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
                price_unit = line._stock_account_get_anglo_saxon_price_unit()
                amount_currency = sign * line.quantity * price_unit

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
                    product_stock_moves = stock_moves.filtered(lambda stock_move: stock_move.product_id == prod)
                    product_account_moves += product_stock_moves.mapped('account_move_ids.line_ids')\
                        .filtered(lambda line: line.account_id == product_interim_account and not line.reconciled)

                    # Reconcile.
                    if any(aml.amount_currency and not aml.balance for aml in product_account_moves):
                        stock_aml = product_account_moves.filtered(lambda aml: aml.move_id.stock_valuation_layer_ids.stock_move_id)
                        invoice_aml = product_account_moves.filtered(lambda aml: aml.move_id == move)
                        correction_amls = product_account_moves - stock_aml - invoice_aml
                        if sum(correction_amls.mapped('balance')) > 0:
                            product_account_moves.with_context(no_exchange_difference=True).reconcile()
                        else:
                            (invoice_aml | correction_amls).with_context(no_exchange_difference=True).reconcile()
                            (invoice_aml | stock_aml).with_context(no_exchange_difference=True).reconcile()
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
            line.product_id.type == 'product'
            and line.move_id.company_id.anglo_saxon_accounting
            and line.move_id.is_purchase_document()
        ))
        for line in input_lines:
            line = line.with_company(line.move_id.journal_id.company_id)
            fiscal_position = line.move_id.fiscal_position_id
            accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if accounts['stock_input']:
                line.account_id = accounts['stock_input']

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

            price_unit = -line.price_unit if move.move_type == 'in_refund' else line.price_unit
            price_unit = price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.tax_ids:
                prec = 1e+6
                price_unit *= prec
                price_unit = line.tax_ids.with_context(round=False).compute_all(
                    price_unit, currency=move.currency_id, quantity=1.0, is_refund=move.move_type == 'in_refund',
                    fixed_multiplicator=move.direction_sign,
                )['total_excluded']
                price_unit /= prec
            layers_price_unit = line._get_stock_valuation_layers_price_unit(layers)
            layers_to_correct = line._get_stock_layer_price_difference(layers, layers_price_unit, price_unit)

            svl_vals_list += line._prepare_in_invoice_svl_vals(layers_to_correct)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _eligible_for_cogs(self):
        self.ensure_one()
        return self.product_id.type == 'product' and self.product_id.valuation == 'real_time'

    def _get_stock_valuation_layers(self, move):
        valued_moves = self._get_valued_in_moves()
        if move.move_type == 'in_refund':
            valued_moves = valued_moves.filtered(lambda stock_move: stock_move._is_out())
        else:
            valued_moves = valued_moves.filtered(lambda stock_move: stock_move._is_in())
        return valued_moves.stock_valuation_layer_ids

    def _get_stock_valuation_layers_price_unit(self, layers):
        price_unit_by_layer = {}
        for layer in layers:
            price_unit_by_layer[layer] = layer.value / layer.quantity
        return price_unit_by_layer

    def _get_stock_layer_price_difference(self, layers, layers_price_unit, price_unit):
        po_line = self.purchase_line_id
        invoice_lines = po_line.invoice_lines - self
        invoices_qty = 0
        for invoice_line in invoice_lines:
            invoices_qty += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, invoice_line.product_id.uom_id)
        layers_to_correct = {}
        for layer in layers:
            if layer.quantity <= invoices_qty:
                invoices_qty -= layer.quantity
                continue
            qty_to_correct = layer.quantity - invoices_qty
            layer_price_unit = self.company_id.currency_id._convert(
                layers_price_unit[layer], po_line.currency_id, self.company_id, self.date, round=False)
            price_difference = price_unit - layer_price_unit
            price_difference = po_line.currency_id._convert(
                price_difference, self.company_id.currency_id, self.company_id, self.date, round=False)
            # TODO convert in invoice currency
            price_difference_curr = (po_line.price_unit - self.price_unit)
            if float_is_zero(price_difference * qty_to_correct, precision_rounding=self.currency_id.rounding):
                continue
            layers_to_correct[layer] = (qty_to_correct, price_difference, price_difference_curr)
        return layers_to_correct

    def _get_valued_in_moves(self):
        return self.env['stock.move']

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
            svl_vals.update(**common_svl_vals, stock_valuation_layer_id=layer.id, price_diff_value=price_difference_curr * quantity)
            svl_vals_list.append(svl_vals)
            # Adds the difference into the last SVL's remaining value.
            layer.remaining_value += svl_vals['value']
            if float_compare(invoiced_qty, 0, self.product_id.uom_id.rounding) <= 0:
                break

        return svl_vals_list

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
