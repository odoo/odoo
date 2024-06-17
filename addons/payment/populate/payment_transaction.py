# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    _populate_dependencies = ['payment.method', 'res.partner']
    _populate_sizes = {'small': 10**3, 'medium': 10**4, 'large': 10**5}

    def _populate_factories(self):
        providers_ids = self.env.registry.populated_models['payment.provider']
        payment_method_ids = self.env.registry.populated_models['payment.method']
        active_currencies_ids = self.env['res.currency'].search([('active', '=', True)]).ids
        partner_ids = self.env.registry.populated_models['res.partner']

        def get_amount(random, *_args, **_kwargs):
            return random.uniform(0, 1000)

        return [
            ('provider_id', populate.randomize(providers_ids)),
            ('payment_method_id', populate.randomize(payment_method_ids)),
            ('reference', populate.constant('reference-{counter}')),
            ('amount', populate.compute(get_amount)),
            ('currency_id', populate.randomize(active_currencies_ids)),
            ('partner_id', populate.randomize(partner_ids)),
        ]
