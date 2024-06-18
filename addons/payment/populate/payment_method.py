# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from odoo import Command, models
from odoo.tools import file_path, populate


_logger = logging.getLogger(__name__)


class PaymentMethod(models.Model):
    _inherit = 'payment.method'
    _populate_dependencies = ['payment.provider']
    _populate_sizes = {'small': 10**2, 'medium': 10**3, 'large': 10**4}

    def _populate_factories(self):
        image_path = file_path('payment/static/img/unknown.png')
        with open(image_path, 'rb') as image_file:
            img = base64.b64encode(image_file.read())
        return [
            ('name', populate.constant('Payment Method {counter}')),
            ('code', populate.constant('code-{counter}')),
            ('image',  populate.constant(img)),
        ]

    def _populate(self, size):
        payment_methods = super()._populate(size)

        _logger.info("Setting payment providers on payment methods.")
        providers_ids = self.env.registry.populated_models['payment.provider']
        r = populate.Random('link_pm_to_providers')
        for pm in payment_methods:
            # TODO comment
            sample_size = r.randint(0, len(providers_ids))
            pm.provider_ids = [Command.set(r.sample(providers_ids, sample_size))]

        return payment_methods

