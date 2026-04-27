# -*- coding: utf-8 -*-
import threading
import time
import json

from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.tools import date_utils
from odoo.exceptions import UserError, ValidationError

STATEMENT_LINE_CREATION_BATCH_SIZE = 500  # When importing transactions, batch the process to commit after importing batch_size


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    online_transaction_identifier = fields.Char("Online Transaction Identifier", readonly=True)
    online_partner_information = fields.Char(readonly=True)
    online_account_id = fields.Many2one(comodel_name='account.online.account', readonly=True)
    online_link_id = fields.Many2one(
        comodel_name='account.online.link',
        related='online_account_id.account_online_link_id',
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
            Some transactions can be marked as "Zero Balancing",
            which is a transaction used at the end of the day to summarize all the transactions
            of the day. As we already manage the details of all the transactions, this one is not
            useful and moreover create duplicates. To deal with that, we cancel the move and so
            the bank statement line.
        """
        # EXTEND account
        bank_statement_lines = super().create(vals_list)
        moves_to_cancel = self.env['account.move']
        for bank_statement_line in bank_statement_lines:
            transaction_details = json.loads(bank_statement_line.transaction_details) if bank_statement_line.transaction_details else {}
            if not transaction_details.get('is_zero_balancing'):
                continue
            moves_to_cancel |= bank_statement_line.move_id
        moves_to_cancel.button_cancel()

        return bank_statement_lines

    @api.model
    def _online_sync_bank_statement(self, transactions, online_account):
        """
         build bank statement lines from a list of transaction and post messages is also post in the online_account of the journal.
         :param transactions: A list of transactions that will be created.
             The format is : [{
                 'id': online id,                  (unique ID for the transaction)
                 'date': transaction date,         (The date of the transaction)
                 'name': transaction description,  (The description)
                 'amount': transaction amount,     (The amount of the transaction. Negative for debit, positive for credit)
             }, ...]
         :param online_account: The online account for this statement
         Return: The number of imported transaction for the journal
        """
        start_time = time.time()
        lines_to_reconcile = self.env['account.bank.statement.line']
        try:
            for journal in online_account.journal_ids:
                # Since the synchronization succeeded, set it as the bank_statements_source of the journal
                journal.sudo().write({'bank_statements_source': 'online_sync'})
                if not transactions:
                    continue

                sorted_transactions = sorted(transactions, key=lambda transaction: transaction['date'])
                total = self.env.context.get('transactions_total') or sum([transaction['amount'] for transaction in transactions])

                # For first synchronization, an opening line is created to fill the missing bank statement data
                any_st_line = self.search_count([('journal_id', '=', journal.id)], limit=1)
                journal_currency = journal.currency_id or journal.company_id.currency_id
                # If there are neither statement and the ending balance != 0, we create an opening bank statement at the day of the oldest transaction.
                # We set the sequence to >1 to ensure the computed internal_index will force its display before any other statement with the same date.
                if not any_st_line and not journal_currency.is_zero(online_account.balance - total):
                    opening_st_line = self.with_context(skip_statement_line_cron_trigger=True).create({
                        'date': sorted_transactions[0]['date'],
                        'journal_id': journal.id,
                        'payment_ref': _("Opening statement: first synchronization"),
                        'amount': online_account.balance - total,
                        'sequence': 2,
                    })
                    lines_to_reconcile += opening_st_line

                filtered_transactions = online_account._get_filtered_transactions(sorted_transactions)

                do_commit = not (hasattr(threading.current_thread(), 'testing') and threading.current_thread().testing)
                if filtered_transactions:
                    # split transactions import in batch and commit after each batch except in testing mode
                    for index in range(0, len(filtered_transactions), STATEMENT_LINE_CREATION_BATCH_SIZE):
                        lines_to_reconcile += self.with_user(SUPERUSER_ID).with_company(journal.company_id).with_context(skip_statement_line_cron_trigger=True).create(filtered_transactions[index:index + STATEMENT_LINE_CREATION_BATCH_SIZE])
                        if do_commit:
                            self.env.cr.commit()
                    # Set last sync date as the last transaction date
                    journal.account_online_account_id.sudo().write({'last_sync': filtered_transactions[-1]['date']})

                if lines_to_reconcile:
                    # 'limit_time_real_cron' defaults to -1.
                    # Manual fallback applied for non-POSIX systems where this key is disabled (set to None).
                    cron_limit_time = tools.config['limit_time_real_cron'] or -1
                    limit_time = (cron_limit_time if cron_limit_time > 0 else 180) - (time.time() - start_time)
                    if limit_time > 0:
                        lines_to_reconcile._cron_try_auto_reconcile_statement_lines(limit_time=limit_time)
        # Catch any configuration error that would prevent creating the entries, reset fetching_status flag and re-raise the error
        # Otherwise flag is never reset and user is under the impression that we are still fetching transactions
        except (UserError, ValidationError) as e:
            self.env.cr.rollback()
            online_account.account_online_link_id._log_information('error', subject=_("Error"), message=str(e))
            self.env.cr.commit()
            raise
        return lines_to_reconcile
