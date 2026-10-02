from odoo import Command, fields, models
from odoo.exceptions import UserError


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
        item pairs or updating existing ones in place. Invoices in a closed tax
        period get a separate adjustment entry. Existing lines live on a posted
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
            tax_lock_date = account_move.company_id._get_user_lock_date('tax_lock_date', ignore_exceptions=True)
            locked = account_move.date <= tax_lock_date

            for invoice_line in invoice_lines:
                cogs_lines = cogs_lines_by_origin.get(invoice_line, account_move.env['account.move.line'])
                accounts = invoice_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=account_move.fiscal_position_id)
                stock_account = accounts['stock_valuation']

                sign = -1 if account_move.move_type == 'out_refund' else 1
                qty = invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, invoice_line.product_id.uom_id)
                price_unit = invoice_line.cogs_move_ids._get_price_unit(include_consigned=True, product=invoice_line.product_id)
                amount = sign * qty * price_unit

                if locked:
                    invoice_line._create_cogs_adjustment(cogs_lines, amount, accounts, tax_lock_date)
                    continue

                if not cogs_lines:
                    missing_line_ids.add(invoice_line.id)
                    continue

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

    def _create_cogs_adjustment(self, cogs_lines, amount, accounts, tax_lock_date):
        """Post only the difference from the original COGS and previous adjustments."""
        self.ensure_one()
        company = self.company_id
        posted_by_account = dict(self._read_group(
            [
                ('cogs_origin_id', '=', self.id),
                ('display_type', '=', 'cogs'),
                ('parent_state', '=', 'posted'),
            ],
            ['account_id'],
            ['balance:sum'],
        ))
        line_vals = []
        cogs_accounts = cogs_lines.account_id or (accounts['stock_valuation'] | (accounts['expense'] or self.move_id.journal_id.default_account_id))
        for account in cogs_accounts:
            line = cogs_lines.filtered(lambda line: line.account_id == account)[:1] or self
            target_balance = -amount if account == accounts['stock_valuation'] else amount
            delta = company.currency_id.round(target_balance - posted_by_account.get(account, 0))
            if company.currency_id.is_zero(delta):
                continue
            line_vals.append(Command.create({
                **line._prepare_cogs_line_vals(),
                'account_id': account.id,
                'balance': delta,
                'quantity': 0,
            }))
        if not line_vals:
            return
        if not accounts['stock_journal']:
            raise UserError(self.env._("Please set the Journal for Inventory Valuation in the settings."))
        adjustment = self.env['account.move'].create({
            'move_type': 'entry',
            'company_id': company.id,
            'journal_id': accounts['stock_journal'].id,
            'date': max(fields.Date.context_today(self), fields.Date.add(tax_lock_date, days=1)),
            'ref': self.env._('COGS adjustment for %(invoice)s', invoice=self.move_id.display_name),
            'line_ids': line_vals,
        })
        adjustment._post()
