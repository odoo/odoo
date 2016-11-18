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
            query = """
                SELECT amount,
                       currency_id,
                       state
                  FROM payment_transaction
                 WHERE sale_order_id in %s
                   AND state in ('authorized', 'pending')
            """
            sale_order_ids = self.env['sale.order'].search([('team_id', '=', team.id)]).ids
            if sale_order_ids:
                self._cr.execute(query, [tuple(sale_order_ids)])
                transactions = self._cr.dictfetchall()
                for line in transactions:
                    line_currency = self.env['res.currency'].browse(line['currency_id'])
                    if line['state'] == 'authorized':
                        team.authorized_payment_transactions_count += 1
                        team.authorized_payment_transactions_amount += line_currency.compute(line['amount'], self.env.user.company_id.currency_id)
                    elif line['state'] == 'pending':
                        team.pending_payment_transactions_count += 1
                        team.pending_payment_transactions_amount += line_currency.compute(line['amount'], self.env.user.company_id.currency_id)
