# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'
    _populate_dependencies = ['res.company']
    _populate_sizes = {'small': 10, 'medium': 10**2, 'large': 10**3}

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models['res.company']

        return [
            ('name', populate.constant('Provider {counter}')),
            ('sequence', populate.randint(0, 100)),
            ('state', populate.constant('test')),
            # ('company_id', populate.randomize(company_ids)),  # TODO uncomment
            ('company_id', populate.constant(self.env.ref('base.main_company').id)),
        ]
