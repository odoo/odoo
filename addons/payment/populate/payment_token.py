# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class PaymentToken(models.Model):
    _inherit = 'payment.token'
    # _populate_dependencies = ['payment.provider', 'payment.method']
    _populate_sizes = {'small': 10, 'medium': 10**2, 'large': 10**4}

    def _populate_factories(self):
        provider = self.env['payment.provider'].browse([1])
        payment_method = self.env['payment.method'].browse([1])
        partner = self.env['res.partner'].browse([1])

        return [
            ('provider_id', populate.compute(lambda **kwargs: provider.id)),
            ('payment_method_id', populate.compute(lambda **kwargs: payment_method.id)),
            ('payment_details', populate.constant('details-{counter}')),
            ('provider_ref', populate.constant('provider-ref')),
            ('partner_id', populate.compute(lambda **kwargs: partner.id)),
        ]
