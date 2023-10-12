# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'razorpay').update({
            'support_tokenization': True,
        })

    # === BUSINESS METHODS ===#

    def _get_validation_amount(self):
        if self.code == 'razorpay':
            return 1.0
        return super()._get_validation_amount()
