# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentTransaction(models.Model):
    _name = 'payment.transaction'
    _inherit = ['payment.transaction', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        # No payment.transactions loaded by default.
        # at a time of importing SOs it will manually load the linked transactions.
        return fields.Domain.FALSE

    @api.model
    def _load_pos_data_fields(self, config):
        return ['amount', 'payment_id']
