# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import date_utils

# TODO remove in master

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
    def _process_payouts(self):
        return

    def send_payout_request(self, notify=True):
        return

    def _fetch_transactions(self, page=1):
        return [], False
