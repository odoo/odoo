# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, Command
from odoo.tools import populate


_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):
    _inherit = 'payment.token'
    _populate_dependencies = ['payment.transaction', 'res.partner']
    _populate_sizes = {'small': 10**2, 'medium': 10**3, 'large': 10**4}

    def _populate_factories(self):
        providers_ids = self.env.registry.populated_models['payment.provider']
        payment_method_ids = self.env.registry.populated_models['payment.method']
        partner_ids = self.env.registry.populated_models['res.partner']

        return [
            ('provider_id', populate.randomize(providers_ids)),
            ('payment_method_id', populate.randomize(payment_method_ids)),
            ('payment_details', populate.constant('details-{counter}')),
            ('provider_ref', populate.constant('ref-{counter}')),
            ('partner_id', populate.randomize(partner_ids)),
        ]

    def _populate(self, size):
        tokens = super()._populate(size)

        _logger.info("Setting payment tokens on payment transaction.")
        # TODO: link transactions
        # TODO comment and clarify
        r = populate.Random('link_token_to_transactions')
        available_tx_ids = self.env.registry.populated_models['payment.transaction'].copy()
        for token in tokens:
            if available_tx_ids:
                sample_size = r.randint(1, len(available_tx_ids))  # TODO too large; this will consume txs too fast
                sample = r.sample(available_tx_ids, sample_size)
                token.transaction_ids = [Command.set(sample)]
                available_tx_ids = [tx_id for tx_id in available_tx_ids if tx_id not in sample]

        return tokens
