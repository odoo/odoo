# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentWizard(models.TransientModel):
    """ Override for the sale quotation onboarding panel. """

    _inherit = 'payment.acquirer.onboarding.wizard'
    _name = 'sale.payment.acquirer.onboarding.wizard'

    def _get_default_payment_method(self):
        return self.env.user.company_id.sale_onboarding_payment_method

    payment_method = fields.Selection([
        ('digital_signature', 'Digital signature, without payment'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('manual', 'Wire Transfer'),
        ('none', 'No digital signature or payment'),
    ], default=_get_default_payment_method)
    #

    def _set_payment_acquirer_onboarding_step_done(self):
        """ Override. """
        self.env.user.company_id.set_onboarding_step_done('sale_onboarding_order_confirmation_state')

    @api.multi
    def add_payment_methods(self, *args, **kwargs):
        self.env.user.company_id.sale_onboarding_payment_method = self.payment_method
        if self.payment_method == 'digital_signature':
            self.env.user.company_id.portal_confirmation_sign = True
        if self.payment_method in ('paypal', 'stripe'):
            self.env.user.company_id.portal_confirmation_pay = True # TODO self.digital_signature
        return super(PaymentWizard, self).add_payment_methods(*args, **kwargs)
