# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import date_utils


class AdyenPayout(models.Model):
    _name = 'adyen.payout'
    _description = 'Adyen for Platforms Payout'

    @api.depends('payout_schedule')
    def _compute_next_scheduled_payout(self):
        today = fields.date.today()
        for adyen_payout_id in self:
            adyen_payout_id.next_scheduled_payout = date_utils.end_of(today, adyen_payout_id.payout_schedule)

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    name = fields.Char('Name', default='Default', required=True)
    code = fields.Char('Account Code')
    payout_allowed = fields.Boolean(related='adyen_account_id.payout_allowed')
    payout_schedule = fields.Selection(string='Schedule', selection=[
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
    ], default='week', required=True)
    next_scheduled_payout = fields.Date('Next scheduled payout', compute=_compute_next_scheduled_payout, store=True)
    transaction_ids = fields.One2many('adyen.transaction', 'adyen_payout_id', string='Transactions')
    last_sync_date = fields.Datetime()

    @api.model
    def create(self, values):
        adyen_payout_id = super(AdyenPayout, self).create(values)
        if not adyen_payout_id.env.context.get('update_from_adyen'):
            response = adyen_payout_id.adyen_account_id._adyen_rpc('v1/create_payout', {
                'accountHolderCode': adyen_payout_id.adyen_account_id.account_holder_code,
            })
            adyen_payout_id.with_context(update_from_adyen=True).write({
                'code': response['accountCode'],
            })
        return adyen_payout_id

    def unlink(self):
        for adyen_payout_id in self:
            adyen_payout_id.adyen_account_id._adyen_rpc('v1/close_payout', {
                'accountCode': adyen_payout_id.code,
            })
        return super(AdyenPayout, self).unlink()

    @api.model
    def _process_payouts(self):
        for adyen_payout_id in self.search([('next_scheduled_payout', '<=', fields.Date.today())]):
            adyen_payout_id.send_payout_request(notify=False)
            adyen_payout_id._compute_next_scheduled_payout()

    def send_payout_request(self, notify=True):
        response = self.adyen_account_id._adyen_rpc('v1/account_holder_balance', {
            'accountHolderCode': self.adyen_account_id.account_holder_code,
        })
        balances = next(account_balance['detailBalance']['balance'] for account_balance in response['balancePerAccount'] if account_balance['accountCode'] == self.code)
        if notify and not balances:
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {'type': 'simple_notification', 'title': _('No pending balance'), 'message': _('No balance is currently awaitng payout.')}
            )
        for balance in balances:
            response = self.adyen_account_id._adyen_rpc('v1/payout_request', {
                'accountCode': self.code,
                'accountHolderCode': self.adyen_account_id.account_holder_code,
                'amount': balance,
            })
            if notify and response['resultCode'] == 'Received':
                currency_id = self.env['res.currency'].search([('name', '=', balance['currency'])])
                value = round(balance['value'] / (10 ** currency_id.decimal_places), 2) # Convert from minor units
                amount = str(value) + currency_id.symbol if currency_id.position == 'after' else currency_id.symbol + str(value)
                message = _('Successfully sent payout request for %s', amount)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Payout Request sent'), 'message': message}
                )

    def _fetch_transactions(self, page=1):
        response = self.adyen_account_id._adyen_rpc('v1/get_transactions', {
            'accountHolderCode': self.adyen_account_id.account_holder_code,
            'transactionListsPerAccount': [{
                'accountCode': self.code,
                'page': page,
            }]
        })
        transaction_list = response['accountTransactionLists'][0]
        return transaction_list['transactions'], transaction_list['hasNextPage']
