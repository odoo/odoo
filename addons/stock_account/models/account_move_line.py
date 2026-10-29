from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_move_id = fields.Many2one('stock.move', index='btree_not_null')
    cogs_move_ids = fields.Many2many(
        "stock.move", string="COGS stock moves",
        help="Inventory moves used to compute COGS values.",
        compute="_compute_cogs_move_ids",
    )

    def _compute_cogs_move_ids(self):
        self.cogs_move_ids = False

    def _set_cogs(self):
        """Re-evaluate the COGS of the originating invoice lines after the value of
        one of their backing stock moves changed, updating the existing COGS journal
        items in place. The lines live on a posted move, so we write them directly
        (bypassing the move-level readonly guard on ``line_ids``) and defer the
        balance check: both sides of the entry are updated symmetrically, so it is
        balanced again once the loop is done."""
        self = self.sudo()  # noqa: PLW0642
        for invoice_line in self.cogs_origin_id:
            account_move = invoice_line.move_id
            if account_move.state != 'posted':
                continue
            invoice_line = invoice_line.with_company(account_move.company_id)
            accounts = invoice_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=account_move.fiscal_position_id)
            stock_account = accounts['stock_valuation']

            sign = -1 if account_move.move_type == 'out_refund' else 1
            qty = invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, invoice_line.product_id.uom_id)
            price_unit = invoice_line.cogs_move_ids._get_price_unit(include_consigned=True, product=invoice_line.product_id)
            amount = sign * qty * price_unit

            cogs_lines = self.filtered(lambda l: l.display_type == 'cogs' and l.cogs_origin_id == invoice_line)
            for line in cogs_lines:
                on_stock_account = line.account_id == stock_account
                line.with_context(check_move_validity=False).write({
                    'price_unit': price_unit if on_stock_account else -price_unit,
                    'amount_currency': -amount if on_stock_account else amount,
                    'balance': -amount if on_stock_account else amount,
                })

    def _get_cogs_value(self):
        """ Get the COGS price unit in the product's default unit of measure.
        """
        self.ensure_one()

        if not self.product_id or self.product_uom_id.is_zero(self.quantity):
            return self.price_unit

        cogs_qty = self._get_cogs_qty()
        if moves := self.cogs_move_ids:
            price_unit = moves._get_price_unit(include_consigned=True, product=self.product_id)
        else:
            if self.product_id.cost_method in ['standard', 'average']:
                price_unit = self.product_id.standard_price
            else:
                price_unit = self.product_id._get_fifo_value(cogs_qty) / cogs_qty if cogs_qty else 0
        line_quantity_uom = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
<<<<<<< 76809808d9536551bbe2988701b35a58ffe51729
        return abs(price_unit * cogs_qty / line_quantity_uom)
||||||| ebdae3c57f17e0dd4093fb9f64433614aa7b590f
        return abs((price_unit * cogs_qty - self._get_posted_cogs_value()) / line_quantity_uom)

    def _get_stock_moves(self):
        return self.env['stock.move']
=======
        cogs_value = (price_unit * cogs_qty - self._get_posted_cogs_value()) / line_quantity_uom
        # The COGS of a credit note is signed when its lines are created
        return -cogs_value if self.move_id.move_type == 'out_refund' else cogs_value

    def _get_stock_moves(self):
        return self.env['stock.move']
>>>>>>> 64bfa7c292c3cd9ebbe601d0a6419eebf06a05b7

    def _get_cogs_qty(self):
        self.ensure_one()
        return (
            self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            * (-1 if self.move_id.move_type == "out_refund" else 1)
        )
<<<<<<< 76809808d9536551bbe2988701b35a58ffe51729
||||||| ebdae3c57f17e0dd4093fb9f64433614aa7b590f

    def _get_posted_cogs_value(self):
        self.ensure_one()
        return 0

    def _get_lines_from_original_invoice(self):
        return self.move_id.reversed_entry_id.line_ids.filtered(
            lambda l: l.display_type == 'cogs' and l.product_id == self.product_id and
            l.product_uom_id == self.product_uom_id and l.price_unit >= 0
        )
=======

    def _get_posted_cogs_value(self):
        self.ensure_one()
        return 0

    def _get_lines_from_original_invoice(self):
        valuation_account = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=self.move_id.fiscal_position_id)['stock_valuation']
        return self.move_id.reversed_entry_id.line_ids.filtered(
            lambda l: l.display_type == 'cogs' and l.product_id == self.product_id and
            l.product_uom_id == self.product_uom_id and l.account_id == valuation_account
        )
>>>>>>> 64bfa7c292c3cd9ebbe601d0a6419eebf06a05b7
