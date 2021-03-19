# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from datetime import datetime
from dateutil.parser import parse
from pytz import UTC

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class AdyenTransaction(models.Model):
    _name = 'adyen.transaction'
    _description = 'Adyen for Platforms Transaction'
    _order = 'date desc'
    _rec_name = 'reference'

    adyen_account_id = fields.Many2one('adyen.account')
    reference = fields.Char('Reference', index=True, required=True)
    total_amount = fields.Float('Total Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    merchant_amount = fields.Float('Merchant Amount')
    fees = fields.Float('Total Fees')
    fixed_fees = fields.Float('Fixed Fees')
    variable_fees = fields.Float('Variable Fees')
    fees_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR'))
    date = fields.Datetime('Date')
    description = fields.Char('Description')

    status = fields.Selection(related='last_status_id.status')
    last_status_id = fields.Many2one('adyen.transaction.status', 'Last Status', compute='_compute_last_status_id', store=True, readonly=True)
    last_status_update = fields.Datetime(related='last_status_id.date', string='Last Status Update')
    status_ids = fields.One2many('adyen.transaction.status', 'adyen_transaction_id', 'Status History')
    payment_method = fields.Char('Payment Method')
    shopper_country_id = fields.Many2one('res.country')
    card_country_id = fields.Many2one('res.country')
    commercial_card = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('unknown', 'Unknown'),
    ], default='unknown')
    dispute_reference = fields.Char('Dispute Reference')

    _sql_constraints = [
        ('reference_unique', 'unique(reference)', 'A transaction with the same reference already exists.'),
    ]

    @api.depends('status_ids')
    def _compute_last_status_id(self):
        self.last_status_id = False
        for transaction in self.filtered('status_ids'):
            transaction.last_status_id = transaction.status_ids.sorted('date')[-1]

    @api.model
    def _handle_notification(self, data):
        adyen_uuid = data.get("additionalData", {}).get("metadata.adyen_uuid") or data.get('adyen_uuid')
        account = self.env['adyen.account'].sudo().search([('adyen_uuid', '=', adyen_uuid)])
        if not account:
            _logger.warning("Received payment notification for non-existing account")
            return

        reference = data.get('originalReference') or data.get('pspReference')
        tx_sudo = self.env['adyen.transaction'].sudo().search([('reference', '=', reference)])

        if not tx_sudo:
            tx_sudo = self.env['adyen.transaction'].sudo().create({
                'adyen_account_id': account.id,
                'reference': reference,
                'description': data.get('merchantReference'),
            })

        event_code = data.get('eventCode')
        additional_data = data.get('additionalData', {})
        if event_code == "AUTHORISATION":
            currency_id = self.env['res.currency'].search([('name', '=', data.get('amount', {}).get('currency'))])
            shopper_country_id = self.env['res.country'].search([('code', '=', additional_data.get('shopperCountry'))])
            commercial_card = additional_data.get('isCardCommercial', 'unknown')
            card_country_id = self.env['res.country'].search([('code', '=', additional_data.get('cardIssuingCountry', additional_data.get('issuerCountry')))])
            tx_sudo.write({
                'reference': data.get('pspReference'),
                'total_amount': data.get('amount', {}).get('value') / (10 ** currency_id.decimal_places),
                'currency_id': currency_id.id,
                'date': parse(data.get('eventDate')).astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'description': data.get('merchantReference'),
                'payment_method': data.get('paymentMethod'),
                'shopper_country_id': shopper_country_id.id,
                'card_country_id': card_country_id.id,
                'commercial_card': commercial_card if commercial_card in ('yes', 'no', 'unknown') else 'unknown',
            })
        elif event_code == 'FEES_UPDATED':
            tx_sudo.fees = data.get('totalFees', {}).get('value', 0) / (10 ** 2)
            tx_sudo.fixed_fees = data.get('fixedFees', {}).get('value', 0) / (10 ** 2)
            tx_sudo.variable_fees = data.get('variableFees', {}).get('value', 0) / (10 ** 2)
            tx_sudo.merchant_amount = data.get('merchantAmount', {}).get('value', 0) / (10 ** 2)
            tx_sudo.total_amount = data.get('totalAmount', {}).get('value', 0) / (10 ** 2)
        elif event_code in ['CHARGEBACK', 'NOTIFICATION_OF_CHARGEBACK']:
            tx_sudo.dispute_reference = data.get('pspReference')
            # TODO the right thing one day.
            tx_sudo.adyen_account_id.message_post(
                body=_('Transaction %s has been CHARGEBACK\'ed: %s', tx_sudo.description or tx_sudo.reference, data.get('reason')),
                subtype_xmlid="mail.mt_comment"
            )

        return tx_sudo

    def _create_missing_tx(self, account_id, transaction, **kwargs):
        currency_id = self.env['res.currency'].search([('name', '=', transaction.get('amount', {}).get('currency'))])
        tx = self.create({
            'adyen_account_id': account_id,
            'reference': transaction.get('pspReference'),
            'merchant_amount': transaction.get('amount', {}).get('value') / (10 ** currency_id.decimal_places),
            'currency_id': currency_id.id,
            'date': parse(transaction.get('creationDate'), '%Y-%m-%dT%H:%M:%S%z').astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'description': transaction.get('description'),
            **kwargs,
        })
        return tx

    def _update_status(self, new_status, date):
        self.ensure_one()

        if not self.status_ids or self.status_ids[0].date != date:
            self.status_ids = [(0, 0, {
                'adyen_transaction_id': self.id,
                'status': new_status,
                'date': date,
            })]

    def _post_transaction_sync(self):
        pass

class AdyenTransactionStatus(models.Model):
    _name = 'adyen.transaction.status'
    _description = 'Transaction Status'
    _order = 'date desc'
    _rec_name = 'status'

    adyen_transaction_id = fields.Many2one('adyen.transaction', required=True, ondelete='cascade')
    status = fields.Selection(string='Status', selection=[
        ('unknown', 'Unknown'),
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
        ('FundTransfer', 'Fund Transfer'),
        ('PendingFundTransfer', 'Pending Fund Transfer'),
        ('ManualCorrected', 'Manual Corrected'),
    ])
    date = fields.Datetime()


class AdyenTransactionPayout(models.Model):
    _name = 'adyen.transaction.payout'
    _description = 'Payout Transaction'
    _order = 'date desc'

    adyen_account_id = fields.Many2one('adyen.account')
    date = fields.Datetime()
    amount = fields.Float('Amount', required=True)
    currency_id = fields.Many2one('res.currency', required=True)
    reference = fields.Char('Reference', index=True, required=True)
    bank_account_id = fields.Many2one('adyen.bank.account')
    status = fields.Selection(string='Type', selection=[
        ('unknown', 'Unknown'),
        ('Payout', 'Payout'),
        ('PayoutReversed', 'Payout Reversed'),
    ], default='unknown')

    def _create_missing_payout(self, account_id, transaction, **kwargs):
        currency_id = self.env['res.currency'].search([('name', '=', transaction.get('amount', {}).get('currency'))])
        bank_account_id = self.env['adyen.bank.account'].search([('bank_account_uuid', '=', transaction.get('bankAccountDetail', {}).get('bankAccountUUID'))])
        tx = self.create({
            'adyen_account_id': account_id,
            'date': parse(transaction.get('creationDate')).astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'amount': transaction.get('amount', {}).get('value') / (10 ** currency_id.decimal_places),
            'currency_id': currency_id.id,
            'reference': transaction.get('pspReference'),
            'bank_account_id': bank_account_id.id,
            'status': transaction.get('transactionStatus'),
            **kwargs,
        })
        return tx

# TODO create chargeback
