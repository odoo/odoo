# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import UTC

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class AdyenTransaction(models.Model):
    _name = 'adyen.transaction'
    _description = 'Adyen for Platforms Transaction'
    _order = 'date desc'

    adyen_account_id = fields.Many2one('adyen.account')
    reference = fields.Char('Reference')
    amount = fields.Float('Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    date = fields.Datetime('Date')
    description = fields.Char('Description')
    status = fields.Selection(string='Type', selection=[
        ('PendingCredit', 'Pending Credit'),
        ('CreditFailed', 'Credit Failed'),
        ('Credited', 'Credited'),
        ('Converted', 'Converted'),
        ('PendingDebit', 'Pending Debit'),
        ('DebitFailed', 'Debit Failed'),
        ('Debited', 'Debited'),
        ('DebitReversedReceived', 'Debit Reversed Received'),
        ('DebitedReversed', 'Debit Reversed'),
        ('ChargebackReceived', 'Chargeback Received'),
        ('Chargeback', 'Chargeback'),
        ('ChargebackReversedReceived', 'Chargeback Reversed Received'),
        ('ChargebackReversed', 'Chargeback Reversed'),
        ('Payout', 'Payout'),
        ('PayoutReversed', 'Payout Reversed'),
        ('FundTransfer', 'Fund Transfer'),
        ('PendingFundTransfer', 'Pending Fund Transfer'),
        ('ManualCorrected', 'Manual Corrected'),
    ])
    adyen_payout_id = fields.Many2one('adyen.payout')

    @api.model
    def sync_adyen_transactions(self):
        ''' Method called by cron to sync transactions from Adyen.
            Updates the status of pending transactions and create missing ones.
        '''
        for payout_id in self.env['adyen.payout'].search([]):
            page = 1
            has_next_page = True
            new_transactions = True
            pending_statuses = ['PendingCredit', 'PendingDebit', 'DebitReversedReceived', 'ChargebackReceived', 'ChargebackReversedReceived', 'PendingFundTransfer']
            pending_transaction_ids = payout_id.transaction_ids.filtered(lambda tr: tr.status in pending_statuses)

            while has_next_page and (new_transactions or pending_transaction_ids):
                # Fetch next transaction page
                transactions, has_next_page = payout_id._fetch_transactions(page)
                for transaction in transactions:
                    transaction_reference = transaction.get('paymentPspReference') or transaction.get('pspReference')
                    transaction_id = payout_id.transaction_ids.filtered(lambda tr: tr.reference == transaction_reference)
                    if transaction_id:
                        new_transactions = False
                        if transaction_id in pending_transaction_ids:
                            # Update transaction status
                            transaction_id.sudo().write({
                                'status': transaction['transactionStatus'],
                            })
                            pending_transaction_ids -= transaction_id
                    else:
                        currency_id = self.env['res.currency'].search([('name', '=', transaction['amount']['currency'])])
                        # New transaction
                        self.env['adyen.transaction'].sudo().create({
                            'adyen_account_id': payout_id.adyen_account_id.id,
                            'reference': transaction_reference,
                            'amount': transaction['amount']['value'] / (10 ** currency_id.decimal_places),
                            'currency_id': currency_id.id,
                            'date': datetime.strptime(transaction['creationDate'], '%Y-%m-%dT%H:%M:%S%z').astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            'description': transaction.get('description'),
                            'status': transaction['transactionStatus'],
                            'adyen_payout_id': payout_id.id,
                        })
                page += 1
