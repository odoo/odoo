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

    def _use_inventory_valuation(self):
        # EXTENDS 'account': dropshipped (or, via `repair`, already-accounted) lines never touch stock.
        self.ensure_one()
        if not super()._use_inventory_valuation():
            return False
        return all(not m._is_dropshipped() for m in self.cogs_move_ids)

    def _stock_account_prepare_cogs_vals(self):
        """ Values of the two COGS journal items (interim + expense) of the invoice line. """
        self.ensure_one()
        move = self.move_id
        if not self._use_inventory_valuation() or self.product_id.valuation != 'real_time':
            return []
        accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
        stock_account = accounts['stock_valuation']
        credit_expense_account = accounts['expense'] or move.journal_id.default_account_id
        if not stock_account or not credit_expense_account:
            return []

        sign = -1 if move.move_type == 'out_refund' else 1
        price_unit = self._get_cogs_value()
        amount_currency = sign * self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id) * price_unit

        common_vals = {
            'name': self.name[:64] if self.name else '',
            'move_id': move.id,
            'partner_id': move.commercial_partner_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'quantity': self.quantity,
            'analytic_distribution': self.analytic_distribution,
            'display_type': 'cogs',
            'tax_ids': [],
            'cogs_origin_id': self.id,
        }
        return [
            dict(common_vals, price_unit=price_unit, amount_currency=-amount_currency, account_id=stock_account.id),
            dict(common_vals, price_unit=-price_unit, amount_currency=amount_currency, account_id=credit_expense_account.id),
        ]

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

    def _get_gross_unit_price(self):
        if self.product_uom_id.is_zero(self.quantity):
            return self.price_unit

        if self.discount != 100:
            if not any(t.price_include for t in self.tax_ids) and self.discount:
                price_unit = self.price_unit * (1 - self.discount / 100)
            else:
                price_unit = self.price_subtotal / self.quantity
        else:
            price_unit = self.price_unit

        return -price_unit if self.move_id.move_type == 'in_refund' else price_unit

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
