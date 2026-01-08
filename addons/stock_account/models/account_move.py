from odoo import fields, models
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_ids = fields.One2many('stock.move', 'account_move_id', string='Stock Move')

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    def _get_lines_onchange_currency(self):
        # OVERRIDE
        return self.line_ids.filtered(lambda l: l.display_type != 'cogs')

    def copy_data(self, default=None):
        # Don't keep anglo-saxon lines when copying a journal entry.
        vals_list = super().copy_data(default=default)

        if not self.env.context.get('move_reverse_cancel'):
            for vals in vals_list:
                if 'line_ids' in vals:
                    vals['line_ids'] = [line_vals for line_vals in vals['line_ids']
                                             if line_vals[0] != 0 or line_vals[2].get('display_type') != 'cogs']
        return vals_list

    def _post(self, soft=True):
        # OVERRIDE

        # Don't change anything on moves used to cancel another ones.
        if self.env.context.get('move_reverse_cancel'):
            return super()._post(soft)

        # Create additional COGS lines for customer invoices.
        self.env['account.move.line'].create(self._stock_account_prepare_realtime_out_lines_vals())

        # Post entries.
        res = super()._post(soft)

        self.line_ids._get_stock_moves().filtered(lambda m: m.is_in)._set_value()

        return res

    def button_draft(self):
        res = super().button_draft()

        # Unlink the COGS lines generated during the 'post' method.
        with self.env.protecting(self.env['account.move']._get_protected_vals({}, self)):
            self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()
        return res

    def button_cancel(self):
        # OVERRIDE
        res = super().button_cancel()

        # Unlink the COGS lines generated during the 'post' method.
        # In most cases it shouldn't be necessary since they should be unlinked with 'button_draft'.
        # However, since it can be called in RPC, better be safe.
        self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()
        return res

    # -------------------------------------------------------------------------
    # COGS METHODS
    # -------------------------------------------------------------------------

    def _stock_account_prepare_realtime_out_lines_vals(self):
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
        500000 COGS (stock variation)               | 9.0   |
        ---------------------------------------------------------------
        110100 Stock Account                        |       | 9.0
        ---------------------------------------------------------------

        Note: COGS are only generated for customer invoices except refund made to cancel an invoice.

        :return: A list of Python dictionary to be passed to env['account.move.line'].create.
        '''
        lines_vals_list = []

        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        for move in self:

            # Make the loop multi-company safe when accessing models like product.product
            move = move.with_company(move.company_id)

            if not move.is_sale_document(include_receipts=True):
                continue

            anglo_saxon_price_ctx = move._get_anglo_saxon_price_ctx()

            for line in move.invoice_line_ids:
                # Filter out lines being not eligible for COGS.
                if not line._eligible_for_stock_account() or line.product_id.valuation != 'real_time':
                    continue
                # Retrieve accounts needed to generate the COGS.
                accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
                stock_account = accounts['stock_valuation']
                credit_expense_account = accounts['expense'] or move.journal_id.default_account_id
                if not stock_account or not credit_expense_account:
                    continue

                # Compute accounting fields.
                sign = -1 if move.move_type == 'out_refund' else 1
                price_unit = line.with_context(anglo_saxon_price_ctx)._get_cogs_value()
                amount_currency = sign * line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id) * price_unit

                if move.currency_id.is_zero(amount_currency) or float_is_zero(price_unit, precision_digits=price_unit_prec):
                    continue

                # Add interim account line.
                lines_vals_list.append({
                    'name': line.name[:64] if line.name else '',
                    'move_id': move.id,
                    'partner_id': move.commercial_partner_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': price_unit,
                    'amount_currency': -amount_currency,
                    'account_id': stock_account.id,
                    'display_type': 'cogs',
                    'tax_ids': [],
                    'cogs_origin_id': line.id,
                })

                # Add expense account line.
                lines_vals_list.append({
                    'name': line.name[:64] if line.name else '',
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
                    'cogs_origin_id': line.id,
                })
        return lines_vals_list

    def _get_anglo_saxon_price_ctx(self):
        """ To be overriden in modules overriding _get_cogs_value
        to optimize computations that only depend on account.move and not account.move.line
        """
        return self.env.context

    def _get_related_stock_moves(self):
        return self.env['stock.move']

    def _get_invoiced_lot_values(self):
        return []
<<<<<<< 9501f8f97c8ff923eae52ece9b9390706fea63fe
||||||| d030a7f939b5029ec895edd56d7350d36d76dabe


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'account_move_line_id', string='Stock Valuation Layer')
    cogs_origin_id = fields.Many2one(  # technical field used to keep track in the originating line of the anglo-saxon lines
        comodel_name="account.move.line",
        copy=False,
        index="btree_not_null",
    )

    def _compute_account_id(self):
        super()._compute_account_id()
        input_lines = self.filtered(lambda line: (
            line._eligible_for_cogs()
            and line.move_id.company_id.anglo_saxon_accounting
            and line.move_id.is_purchase_document()
        ))
        for line in input_lines:
            fiscal_position = line.move_id.fiscal_position_id
            accounts = line.with_company(line.company_id).product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if accounts['stock_input']:
                line.account_id = accounts['stock_input']

    def _eligible_for_cogs(self):
        self.ensure_one()
        return self.product_id.is_storable and self.product_id.valuation == 'real_time'

    def _get_gross_unit_price(self):
        if float_is_zero(self.quantity, precision_rounding=self.product_uom_id.rounding):
            return self.price_unit

        if self.discount != 100:
            if not any(t.price_include for t in self.tax_ids) and self.discount:
                price_unit = self.price_unit * (1 - self.discount / 100)
            else:
                price_unit = self.price_subtotal / self.quantity
        else:
            price_unit = 0

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

    def _get_exchange_journal(self, company):
        if (
            self and self.move_id.sudo().stock_valuation_layer_ids and
            self.product_id.categ_id.property_valuation == 'real_time'
        ):
            return self.product_id.categ_id.property_stock_journal
        return super()._get_exchange_journal(company)

    def _get_exchange_account(self, company, amount):
        if (
            self and self.move_id.sudo().stock_valuation_layer_ids and
            self.product_id.categ_id.property_valuation == 'real_time'
        ):
            return self.product_id.categ_id.property_stock_valuation_account_id
        return super()._get_exchange_account(company, amount)
=======


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'account_move_line_id', string='Stock Valuation Layer')
    cogs_origin_id = fields.Many2one(  # technical field used to keep track in the originating line of the anglo-saxon lines
        comodel_name="account.move.line",
        copy=False,
        index="btree_not_null",
    )

    def _compute_account_id(self):
        super()._compute_account_id()
        input_lines = self.filtered(lambda line: (
            line._eligible_for_cogs()
            and line.move_id.company_id.anglo_saxon_accounting
            and line.move_id.is_purchase_document()
        ))
        for line in input_lines:
            fiscal_position = line.move_id.fiscal_position_id
            accounts = line.with_company(line.company_id).product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if accounts['stock_input']:
                line.account_id = accounts['stock_input']

    def _eligible_for_cogs(self):
        self.ensure_one()
        return self.product_id.is_storable and self.product_id.valuation == 'real_time'

    def _get_gross_unit_price(self):
        if float_is_zero(self.quantity, precision_rounding=self.product_uom_id.rounding):
            return self.price_unit

        if self.discount != 100:
            if not any(t.price_include for t in self.tax_ids) and self.discount:
                price_unit = self.price_unit * (1 - self.discount / 100)
            else:
                price_unit = self.price_subtotal / self.quantity
        else:
            price_unit = 0

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

    def _get_exchange_journal(self, company):
        if (
            self and self.move_id.sudo().stock_valuation_layer_ids and
            self.product_id.categ_id.property_cost_method != 'standard' and
            self.product_id.categ_id.property_valuation == 'real_time'
        ):
            return self.product_id.categ_id.property_stock_journal
        return super()._get_exchange_journal(company)

    def _get_exchange_account(self, company, amount):
        if (
            self and self.move_id.sudo().stock_valuation_layer_ids and
            self.product_id.categ_id.property_cost_method != 'standard' and
            self.product_id.categ_id.property_valuation == 'real_time'
        ):
            return self.product_id.categ_id.property_stock_valuation_account_id
        return super()._get_exchange_account(company, amount)
>>>>>>> 16347be206654451a4d613f9565c076f619cc549
