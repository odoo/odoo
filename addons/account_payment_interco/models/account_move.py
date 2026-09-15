from odoo import Command, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _interco_filter_moves(self):
        return self.filtered(lambda m:
            m.is_invoice()
            and m.payment_state in ('not_paid', 'partial', 'in_payment')
            and m.company_id.account_interco_clearing_journal_id
            and m.transaction_ids.payment_id
            and m.company_id not in m.transaction_ids.payment_id.company_id
            and ((
                m.is_inbound()
                and m.company_id.account_interco_receivable_id
                and m.transaction_ids.payment_id.company_id.account_interco_payable_id
            ) or (
                m.is_outbound()
                and m.company_id.account_interco_payable_id
                and m.transaction_ids.payment_id.company_id.account_interco_receivable_id
            ))
            and m.transaction_ids.payment_id.filtered(
                lambda x: x.state in ('in_process', 'paid')
                      and x.company_id != m.company_id
                      and x.company_id.account_interco_clearing_journal_id.id
            )
        )

    def _post(self, soft=True):
        """ Check if there are pending payments on other companies that wait for this move. """
        moves = super()._post(soft)
        if interco_moves := moves.sudo()._interco_filter_moves():
            for invoice in interco_moves:
                transactions = invoice.sudo().transaction_ids.filtered(lambda tx: tx.state in ('authorized', 'done'))
                invoice._check_interco_clearing(transactions.payment_id)
        return moves

    def _check_interco_clearing(self, payments):
        self.ensure_one()

        is_sale = self.is_sale_document()
        label = f"{self.partner_id.display_name} / {self.name}"

        for payment in payments:
            _liquidity_lines, counterpart_lines, _writeoff_lines = payment._seek_for_lines()
            if counterpart_lines:
                counterpart_account = counterpart_lines.account_id
                clearing_balance = -sum(line.balance for line in counterpart_lines)
                clearing_amount_currency = -sum(line.amount_currency for line in counterpart_lines)

                other_interco_account = (
                    payment.company_id.account_interco_payable_id
                    if is_sale
                    else payment.company_id.account_interco_receivable_id
                )
                payment_clearing = self.env['account.move'].with_company(payment.company_id).create({
                    'move_type': 'entry',
                    'journal_id': payment.company_id.account_interco_clearing_journal_id.id,
                    'ref': payment.memo,
                    'line_ids': [
                        Command.create({
                            'name': label,
                            'account_id': counterpart_account.id,
                            'partner_id': self.partner_id.id,
                            'currency_id': payment.currency_id.id,
                            'amount_currency': clearing_amount_currency,
                            'balance': clearing_balance
                        }),
                        Command.create({
                            'name': label,
                            'account_id': other_interco_account.id,
                            'partner_id': self.company_id.partner_id.id,
                            'currency_id': payment.currency_id.id,
                            'amount_currency': -clearing_amount_currency,
                            'balance': -clearing_balance
                        }),
                    ]
                })
                payment_clearing.action_post()
                payment_clearing_line = payment_clearing.line_ids.filtered(lambda line: line.account_id == counterpart_account)
                (counterpart_lines + payment_clearing_line).reconcile()

        payment = payments[0]
        invoice_lines = self.line_ids.filtered(lambda acc: acc.account_type in ('asset_receivable', 'liability_payable'))
        invoice_line_account = invoice_lines[:1].account_id
        total_invoice_balance = sum(invoice_lines.mapped('balance'))
        clearing_counterpart_balance = -total_invoice_balance

        self_interco_account = (
            self.company_id.account_interco_receivable_id
            if is_sale
            else self.company_id.account_interco_payable_id
        )
        memos = ", ".join(payments.mapped("memo"))
        entry = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'entry',
            'journal_id': self.company_id.account_interco_clearing_journal_id.id,
            'ref': self.env._("Interco Settlement - %s", memos),
            'line_ids': [
                Command.create({
                    'name': label,
                    'account_id': self_interco_account.id,
                    'partner_id': payment.company_id.partner_id.id,
                    'currency_id': self.company_id.currency_id.id,
                    'balance': -clearing_counterpart_balance,
                }),
                Command.create({
                    'name': label,
                    'account_id': invoice_line_account.id,
                    'partner_id': payment.partner_id.id,
                    'currency_id': self.company_id.currency_id.id,
                    'balance': clearing_counterpart_balance,
                }),
            ],
        })
        entry.action_post()

        entry_receivable_line = entry.line_ids.filtered(lambda line: line.account_id == invoice_line_account)
        (entry_receivable_line + invoice_lines).reconcile()
