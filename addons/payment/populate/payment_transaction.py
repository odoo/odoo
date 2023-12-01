# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    # _populate_dependencies = ['payment.provider', 'payment.method']
    _populate_sizes = {'small': 10**2, 'medium': 10**3, 'large': 10**5}

    def _populate_factories(self):
        provider = self.env['payment.provider'].browse([1])
        payment_method = self.env['payment.method'].browse([1])
        currency = self.env['res.currency'].browse([1])
        partner = self.env['res.partner'].browse([1])

        def get_amount(random, **kwargs):
            return random.uniform(0, 1000)

        return [
            ('provider_id', populate.compute(lambda **kwargs: provider.id)),
            ('payment_method_id', populate.compute(lambda **kwargs: payment_method.id)),
            ('reference', populate.constant('reference-{counter}')),
            ('amount', populate.compute(get_amount)),
            ('currency_id', populate.compute(lambda **kwargs: currency.id)),
            ('partner_id', populate.compute(lambda **kwargs: partner.id)),
        ]
