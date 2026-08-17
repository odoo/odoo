from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_ids = fields.One2many('stock.move', 'account_move_id', string='Stock Move')
    inventory_closing = fields.Boolean(string='Inventory Closing', default=False)
    closing_datetime = fields.Datetime(string='Closing Date')

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    def _update_average_cost_on_hand(self):
        # the cost is updated at stock move validation when stock is installed
        pass

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

        self.line_ids.cogs_move_ids.filtered(lambda m: m.is_in or m.is_dropship)._set_value()

        return res

    def button_draft(self):
        res = super().button_draft()

        # Unlink the COGS lines generated during the 'post' method.
        with self.env.protecting(self.env['account.move']._get_protected_vals({}, self)):
            self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()

        self.line_ids.cogs_move_ids.filtered(lambda m: m.is_in or m.is_dropship)._set_value()
        return res

    def button_cancel(self):
        # OVERRIDE
        res = super().button_cancel()

        # Unlink the COGS lines generated during the 'post' method.
        # In most cases it shouldn't be necessary since they should be unlinked with 'button_draft'.
        # However, since it can be called in RPC, better be safe.
        self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()

        self.line_ids.cogs_move_ids.filtered(lambda m: m.is_in or m.is_dropship)._set_value()
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
        for move in self:
            # Make the loop multi-company safe when accessing models like product.product
            move = move.with_company(move.company_id)
            if not move.is_sale_document(include_receipts=True):
                continue
            anglo_saxon_price_ctx = move._get_anglo_saxon_price_ctx()
            for line in move.invoice_line_ids:
                lines_vals_list += line.with_context(anglo_saxon_price_ctx)._stock_account_prepare_cogs_vals()
        return lines_vals_list

    def _get_anglo_saxon_price_ctx(self):
        """ To be overriden in modules overriding _get_cogs_value
        to optimize computations that only depend on account.move and not account.move.line
        """
        return self.env.context

    def _update_standard_price(self, reverse=False):
        return

    def _get_invoiced_lot_values(self):
        return []

    def _extract_extra_invoiced_lot_values(self, lot):
        lot.ensure_one()
        # Compute lot properties
        lot_properties = lot.product_id.lot_properties_definition
        # Store the value of each property
        for prop in lot_properties:
            prop['value'] = lot.lot_properties.get(prop['name'])
        return {'lot_properties': lot_properties}
