# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from pytz import UTC

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.adyen_platforms.util import to_major_currency, to_minor_currency

_logger = logging.getLogger(__name__)


class AdyenTransaction(models.Model):
    _name = 'adyen.transaction'
    _description = 'Adyen for Platforms Transaction'
    _order = 'date desc'
    _rec_name = 'reference'

    adyen_account_id = fields.Many2one('adyen.account')
    reference = fields.Char('Reference', index=True, required=True)
    capture_reference = fields.Char('Capture Reference')
    total_amount = fields.Float('Customer Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    merchant_amount = fields.Float('Merchant Amount')
    fees = fields.Float('Fees')
    fixed_fees = fields.Float('Fixed Fees')
    variable_fees = fields.Float('Variable Fees')
    fees_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR'))
    date = fields.Datetime('Date')
    description = fields.Char('Description')
    signature = fields.Char('Signature')
    reason = fields.Char('Failure Reason')

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
        ('reference_unique', 'unique(reference, capture_reference)', 'A transaction with the same reference already exists.'),
    ]

    @api.depends('status_ids')
    def _compute_last_status_id(self):
        self.last_status_id = False
        for transaction in self.filtered('status_ids'):
            transaction.last_status_id = transaction.status_ids.sorted('date')[-1]

    def _get_tx_from_notification(self, notification):
        if notification.get('eventCode') in ['CAPTURE', 'REFUND']:
            reference = notification.get('originalReference')
            capture_reference = notification.get('pspReference')
        else:
            reference = notification.get('pspReference')
            capture_reference = notification.get('capturePspReference')

        domain = [('reference', '=', reference)]
        if capture_reference:
            domain = expression.AND([domain, [('capture_reference', '=', capture_reference)]])

        if self:
            return self.filtered_domain(domain), reference, capture_reference
        return self.env['adyen.transaction'].search(domain), reference, capture_reference

    @api.model
    def _handle_notification(self, data):
        adyen_uuid = data.get("additionalData", {}).get("metadata.adyen_uuid") or data.get('adyen_uuid')
        account = self.env['adyen.account'].sudo().search([('adyen_uuid', '=', adyen_uuid)])
        if not account:
            _logger.warning("Received payment notification for non-existing account")
            return

        tx_sudo, reference, capture_reference = self.env['adyen.transaction']._get_tx_from_notification(data)
        if not tx_sudo:
            tx_sudo = self.env['adyen.transaction'].sudo().create({
                'adyen_account_id': account.id,
                'reference': reference,
                'capture_reference': capture_reference,
                'description': data.get('merchantReference'),
            })

        event_code = data.get('eventCode')
        if event_code == "AUTHORISATION":
            tx_sudo._handle_authorisation_notification(data)
        elif event_code == "FEES_UPDATED":
            tx_sudo._handle_fees_updated_notification(data)
        elif event_code == "REFUND":
            tx_sudo._handle_refund_notification(data)
        elif event_code in ["CHARGEBACK", "NOTIFICATION_OF_CHARGEBACK"]:
            tx_sudo._handle_chargeback_notification(data)
        else:
            _logger.warning(_("Unknown eventCode received: %s", event_code))

        return tx_sudo

    def _handle_authorisation_notification(self, notification_data):
        self.ensure_one()
        additional_data = notification_data.get('additionalData', {})

        currency_id = self.env['res.currency'].search([('name', '=', notification_data.get('amount', {}).get('currency'))])
        shopper_country_id = self.env['res.country'].search([('code', '=', additional_data.get('shopperCountry'))])
        commercial_card = additional_data.get('isCardCommercial', 'unknown')
        card_country_id = self.env['res.country'].search([('code', '=', additional_data.get('cardIssuingCountry', additional_data.get('issuerCountry')))])

        self.write({
            'reference': notification_data.get('pspReference'),
            'total_amount': to_major_currency(notification_data['amount']['value'], currency_id.decimal_places),
            'currency_id': currency_id.id,
            'date': parse(notification_data.get('eventDate')).astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'description': notification_data.get('merchantReference'),
            'payment_method': notification_data.get('paymentMethod'),
            'shopper_country_id': shopper_country_id.id,
            'card_country_id': card_country_id.id,
            'commercial_card': commercial_card if commercial_card in ('yes', 'no', 'unknown') else 'unknown',
        })
        self._trigger_sync()

    def _handle_fees_updated_notification(self, notification_data):
        self.ensure_one()

        currency_amount = self.env['res.currency'].search([('name', '=', notification_data.get('totalAmount', {}).get('currency'))])
        currency_fees = self.env['res.currency'].search([('name', '=', notification_data.get('totalFees', {}).get('currency'))])
        self.capture_reference = notification_data.get('captureReference')
        self.fees = to_major_currency(notification_data['totalFees']['value'], currency_fees.decimal_places)
        self.fixed_fees = to_major_currency(notification_data['fixedFees']['value'], currency_fees.decimal_places)
        self.variable_fees = to_major_currency(notification_data['variableFees']['value'], currency_fees.decimal_places)
        self.merchant_amount = to_major_currency(notification_data['merchantAmount']['value'], currency_amount.decimal_places)
        self.total_amount = to_major_currency(notification_data['totalAmount']['value'], currency_amount.decimal_places)
        self.signature = notification_data.get('signature')

    def _handle_refund_notification(self, notification_data):
        self.ensure_one()

        currency_id = self.env['res.currency'].search([('name', '=', notification_data.get('amount', {}).get('currency'))])
        self.currency_id = currency_id.id
        self.date = parse(notification_data.get('eventDate')).astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        reason = notification_data.get('reason')
        if reason:
            self.reason = reason

    def _handle_chargeback_notification(self, notification_data):
        self.ensure_one()
        self.dispute_reference = notification_data.get('pspReference')

        self.adyen_account_id.message_post(
            body=_('Transaction %s has been CHARGEBACK\'ed: %s', self.description or self.reference, notification_data.get('reason')),
            subtype_xmlid="mail.mt_comment"
        )

    def _create_missing_tx(self, account_id, transaction, **kwargs):
        currency_id = self.env['res.currency'].search([('name', '=', transaction.get('amount', {}).get('currency'))])
        amount = to_major_currency(transaction['amount']['value'], currency_id.decimal_places)
        tx = self.create({
            'adyen_account_id': account_id,
            'reference': transaction.get('pspReference'),
            'capture_reference': transaction.get('capturePspReference'),
            'merchant_amount': amount,
            'total_amount': amount,
            'currency_id': currency_id.id,
            'date': parse(transaction.get('creationDate')).astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'description': transaction.get('description'),
            **kwargs,
        })
        return tx

    def _trigger_sync(self):
        sync_cron = self.env.ref('adyen_platforms.adyen_sync_cron', raise_if_not_found=False)
        if sync_cron:
            sync_cron._trigger(at=fields.Datetime.now() + relativedelta(minutes=5))

    def _update_status(self, new_status, date):
        self.ensure_one()

        if not self.status_ids or self.status_ids[0].date != date:
            self.status_ids = [(0, 0, {
                'adyen_transaction_id': self.id,
                'status': new_status,
                'date': date,
            })]

    def _post_transaction_sync(self):
        """ Hook defined to perform actions on transactions after they were sync'ed """
        return

    def _refund_request(self, amount=None):
        self.ensure_one()

        if amount is None:
            amount = self.total_amount

        if amount > self.total_amount:
            raise ValidationError(_('You cannot refund more than the original amount.'))

        converted_amount = to_minor_currency(amount, self.currency_id.decimal_places)
        initial_amount = to_minor_currency(self.total_amount, self.currency_id.decimal_places)
        fees_amount = to_minor_currency(self.fees, self.fees_currency_id.decimal_places)

        refund_data = {
            'originalReference': self.reference,
            'modificationAmount': {
                'currency': self.currency_id.name,
                'value': converted_amount,
            },
            'initialAmount': {
                'currency': self.currency_id.name,
                'value': initial_amount,
            },
            'feesAmount': {
                'currency': self.fees_currency_id.name,
                'value': fees_amount,
            },
            'date': str(self.date),
            'reference': 'Refund of %s' % self.description, # TODO generate unique reference
            'payout': self.adyen_account_id.account_code,
            'adyen_uuid': self.adyen_account_id.adyen_uuid,
            'signature': self.signature,
        }
        res = self.adyen_account_id._adyen_rpc('v1/refund', refund_data)

        refund_tx = self.env['adyen.transaction'].sudo().create({
            'adyen_account_id': self.adyen_account_id.id,
            'reference': self.reference,
            'capture_reference': res['pspReference'],
            'description': refund_data.get('reference'),
            'currency_id': self.currency_id.id,
            'total_amount': to_major_currency(res['totalAmount']['value'], self.currency_id.decimal_places),
            'fees': to_major_currency(res['totalFees']['value'], self.currency_id.decimal_places),
            'variable_fees': to_major_currency(res['totalFees']['value'], self.currency_id.decimal_places),
            'merchant_amount': to_major_currency(res['merchantAmount']['value'], self.currency_id.decimal_places),
            'date': fields.Datetime.now(),
        })
        self._trigger_sync()

        return refund_tx

    def action_refund(self):
        for tx in self:
            tx._refund_request()


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
        currency_id = self.env['res.currency'].search([('name', '=', transaction['amount']['currency'])])
        bank_account_id = self.env['adyen.bank.account'].search([('bank_account_uuid', '=', transaction.get('bankAccountDetail', {}).get('bankAccountUUID'))])
        tx = self.create({
            'adyen_account_id': account_id,
            'date': parse(transaction.get('creationDate')).astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'amount': to_major_currency(transaction.get('amount', {}).get('value'), currency_id.decimal_places),
            'currency_id': currency_id.id,
            'reference': transaction.get('pspReference'),
            'bank_account_id': bank_account_id.id,
            'status': transaction.get('transactionStatus'),
            **kwargs,
        })
        return tx
