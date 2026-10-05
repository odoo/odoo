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
        one of their backing stock moves changed, creating missing COGS journal
        item pairs or updating existing ones in place. The lines live on a posted
        move, so we write them directly (bypassing the move-level readonly guard
        on ``line_ids``) and defer the balance check until both sides are updated.
        """
        for account_move, invoice_lines in self.sudo().grouped('move_id').items():
            if account_move.state != 'posted' or not account_move.is_sale_document(include_receipts=True):
                continue

            account_move = account_move.with_company(account_move.company_id)
            invoice_lines = invoice_lines.with_company(account_move.company_id)
            cogs_lines_by_origin = account_move.line_ids.filtered(lambda line: line.display_type == 'cogs' and line.cogs_origin_id).grouped('cogs_origin_id')
            missing_line_ids = set()

            for invoice_line in invoice_lines:
                cogs_lines = cogs_lines_by_origin.get(invoice_line, account_move.env['account.move.line'])
                if not cogs_lines:
                    missing_line_ids.add(invoice_line.id)
                    continue

                accounts = invoice_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=account_move.fiscal_position_id)
                stock_account = accounts['stock_valuation']

                sign = -1 if account_move.move_type == 'out_refund' else 1
                qty = invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, invoice_line.product_id.uom_id)
                price_unit = invoice_line.cogs_move_ids._get_price_unit(include_consigned=True, product=invoice_line.product_id)
                amount = sign * qty * price_unit

                for line in cogs_lines:
                    on_stock_account = line.account_id == stock_account
                    line.with_context(check_move_validity=False).write({
                        'price_unit': price_unit if on_stock_account else -price_unit,
                        'amount_currency': -amount if on_stock_account else amount,
                        'balance': -amount if on_stock_account else amount,
                    })

            if missing_line_ids:
                invoice_lines.create([vals for vals in account_move._get_cogs_lines_vals() if vals['cogs_origin_id'] in missing_line_ids])

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
        return abs(price_unit * cogs_qty / line_quantity_uom)

    def _get_cogs_qty(self):
        self.ensure_one()
        return (
            self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            * (-1 if self.move_id.move_type == "out_refund" else 1)
        )
