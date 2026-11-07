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
        one of their backing stock moves changed.

        If the invoice is in an open period, the existing COGS journal items are
        updated in place. If it is in a locked period (or has already been adjusted
        by an earlier correction entry), a single delta entry is posted on the first
        open accounting date instead."""
        self = self.sudo()  # noqa: PLW0642

        for invoice_line in self.cogs_origin_id:
            account_move = invoice_line.move_id
            if account_move.state != 'posted':
                continue

            company = account_move.company_id
            invoice_line = invoice_line.with_company(company)
            accounts = invoice_line.product_id.product_tmpl_id.get_product_accounts(
                fiscal_pos=account_move.fiscal_position_id,
            )
            stock_account = accounts['stock_valuation']

            sign = -1 if account_move.move_type == 'out_refund' else 1
            qty = invoice_line.product_uom_id._compute_quantity(
                invoice_line.quantity, invoice_line.product_id.uom_id,
            )
            price_unit = invoice_line.cogs_move_ids._get_price_unit(
                include_consigned=True, product=invoice_line.product_id,
            )
            currency = company.currency_id
            new_amount = currency.round(sign * qty * price_unit)

            all_cogs_lines = self.env['account.move.line'].search([
                ('display_type', '=', 'cogs'),
                ('cogs_origin_id', '=', invoice_line.id),
                ('parent_state', '=', 'posted'),
            ])
            original_lines = all_cogs_lines.filtered(lambda l: l.move_id == account_move)
            adjustment_lines = all_cogs_lines - original_lines

            violated_lock_dates = account_move._get_violated_lock_dates(
                account_move.date, bool(account_move.line_ids.tax_ids),
            )

            if not violated_lock_dates and not adjustment_lines:
                for line in original_lines:
                    on_stock_account = line.account_id == stock_account
                    line.with_context(check_move_validity=False).write({
                        'price_unit': price_unit if on_stock_account else -price_unit,
                        'amount_currency': -new_amount if on_stock_account else new_amount,
                        'balance': -new_amount if on_stock_account else new_amount,
                    })
                continue

            # Locked period (or already adjusted): post one delta per account.
            delta_vals = []
            for account in all_cogs_lines.account_id:
                lines = all_cogs_lines.filtered(lambda l, acc=account: l.account_id == acc)
                target_balance = -new_amount if account == stock_account else new_amount
                delta = currency.round(target_balance - sum(lines.mapped('balance')))
                if currency.is_zero(delta):
                    continue
                delta_vals.append((0, 0, {
                    'name': f"COGS adjustment: {invoice_line.name}",
                    'account_id': account.id,
                    'product_id': invoice_line.product_id.id,
                    'balance': delta,
                    'amount_currency': delta,
                    'currency_id': currency.id,
                    'display_type': 'cogs',
                    'cogs_origin_id': invoice_line.id,
                }))

            if not delta_vals:
                continue

            journal = accounts.get('stock_journal') or account_move.journal_id
            has_tax = False
            adjustment_date = account_move._get_accounting_date(
                fields.Date.context_today(self), has_tax,
            )
            self.env['account.move'].create({
                'move_type': 'entry',
                'date': adjustment_date,
                'journal_id': journal.id,
                'company_id': company.id,
                'ref': f"COGS adjustment for {account_move.name}",
                'line_ids': delta_vals,
            })._post()

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
