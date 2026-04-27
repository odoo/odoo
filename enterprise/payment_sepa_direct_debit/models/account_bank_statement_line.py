# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby

from odoo import api, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.model_create_multi
    def create(self, vals_list):
        statement_lines = super().create(vals_list)

        sepa_cron = self.env.ref('payment_sepa_direct_debit.cron_auto_confirm_paid_sepa_txs', False)
        if sepa_cron:
            sepa_cron._trigger()

        return statement_lines

    def _cron_confirm_sepa_transactions(self):
        """ Confirm pending SEPA payment transactions for which a matching bank statement is found.

        Note: This method is called by the `cron_auto_confirm_paid_sepa_txs` cron.

        :return: None
        """
        pending_sepa_txs = self.env['payment.transaction'].search([
            ('provider_id.code', '=', 'custom'),
            ('provider_id.custom_mode', '=', 'sepa_direct_debit'),
            ('state', '=', 'pending'),
            ('mandate_id', '!=', False),
        ])
        if not pending_sepa_txs:
            return

        currency_euro = self.env['res.currency'].search([('name', '=', 'EUR')], limit=1)
        if not currency_euro:
            return

        for company, txs_list in groupby(pending_sepa_txs, key=lambda tx: tx.company_id):
            txs_list = list(txs_list)
            statement_lines = self.search([
                ('payment_ref', 'in', [tx.reference for tx in txs_list]),
                ('company_id', '=', company.id),
                '|',
                ('currency_id', '=', currency_euro.id),
                ('foreign_currency_id', '=', currency_euro.id),
            ])
            if not statement_lines:
                continue

            for tx in txs_list:
                if any(
                    line.payment_ref == tx.reference
                    and (
                        line.partner_id == tx.partner_id.commercial_partner_id
                        or (
                            not line.partner_id
                            and line.partner_name == tx.partner_id.commercial_partner_id.name
                        )
                    )
                    and (
                        not line.account_number
                        or line.account_number == tx.mandate_id.partner_bank_id.sanitized_acc_number
                    )
                    and (
                        (
                            line.currency_id == tx.currency_id
                            and tx.currency_id.compare_amounts(line.amount, tx.amount) == 0
                        )
                        or (
                            line.foreign_currency_id == tx.currency_id
                            and tx.currency_id.compare_amounts(line.amount_currency, tx.amount) == 0
                        )
                    )
                    for line in statement_lines
                ):
                    tx._set_done()
