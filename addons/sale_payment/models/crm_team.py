# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    pending_payment_transactions_count = fields.Integer(
        compute='_compute_payment_transactions',
        string='Number of pending transactions', readonly=True)
    pending_payment_transactions_amount = fields.Integer(
        compute='_compute_payment_transactions',
        string='Amount of pending transactions', readonly=True)
    authorized_payment_transactions_count = fields.Integer(
        compute='_compute_payment_transactions',
        string='Number of transactions to capture', readonly=True)
    authorized_payment_transactions_amount = fields.Integer(
        compute='_compute_payment_transactions',
        string='Amount of transactions to capture', readonly=True)

    def _compute_payment_transactions(self):
        for team in self:
            payment_data = self.env['payment.transaction'].read_group([
                ('state', 'in', ['authorized', 'pending']),
                ('sale_order_id.team_id', '=', team.id)
            ], ['amount', 'currency_id', 'state'], ['state', 'currency_id'], lazy=False)
            for datum in payment_data:
                datum_currency = self.env['res.currency'].browse(datum['currency_id'][0])
                if datum['state'] == 'authorized':
                    team.authorized_payment_transactions_count += datum['__count']
                    team.authorized_payment_transactions_amount += datum_currency.compute(datum['amount'], self.env.user.company_id.currency_id)
                elif datum['state'] == 'pending':
                    team.pending_payment_transactions_count += datum['__count']
                    team.pending_payment_transactions_amount += datum_currency.compute(datum['amount'], self.env.user.company_id.currency_id)
