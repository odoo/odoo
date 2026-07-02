# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentTransaction(models.Model):
    _name = 'payment.transaction'
    _inherit = ['payment.transaction', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        transaction_ids = [
            tx_id
            for sale_order in data['sale.order']
            for tx_id in sale_order['transaction_ids']
        ]
        return [
            ('state', 'in', ['done', 'authorized']),
            ('id', 'in', transaction_ids)
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['amount', 'payment_id']
