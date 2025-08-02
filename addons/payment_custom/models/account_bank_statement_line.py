# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby

from odoo import api, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.model_create_multi
    def create(self, vals_list):
        statement_lines = super().create(vals_list)

        wire_transfer_cron = self.env.ref('payment_custom.cron_auto_confirm_paid_wire_transfer_txs', False)
        if wire_transfer_cron:
            wire_transfer_cron._trigger()

        return statement_lines

    def _cron_confirm_wire_transfer_transactions(self):
        """ Confirm pending wire transfer payment transactions for which a matching bank statement is found.

        Note: This method is called by the `cron_auto_confirm_paid_wire_transfer_txs` cron.
        :return: None
        """

        pending_wire_transfer_txs = self.env['payment.transaction'].search([
            ('payment_method_id.code', '=', 'wire_transfer'),
            ('state', '=', 'pending'),
        ])
        if not pending_wire_transfer_txs:
            return

        for company, txs_list in groupby(pending_wire_transfer_txs, key=lambda tx: tx.company_id):
            txs_list = list(txs_list)
            statement_lines = self.search([
                ('payment_ref', 'in', [tx.reference for tx in txs_list]),
                ('company_id', '=', company.id),
            ])
            if not statement_lines:
                continue

            for tx in txs_list:
                if any(
                    line.payment_ref == tx.reference
                    and line.partner_id == tx.partner_id.commercial_partner_id
                    and (
                        line.currency_id == tx.currency_id
                        and tx.currency_id.compare_amounts(line.amount, tx.amount) == 0
                    )
                    for line in statement_lines
                ):
                    tx._set_done()
                    tx._post_process()
