# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentWizard(models.TransientModel):
    """ Override for the sale quotation onboarding panel. """

    _inherit = 'payment.acquirer.onboarding.wizard'
    _name = 'sale.payment.acquirer.onboarding.wizard'
    _description = 'Sale Payment acquire onboarding wizard'

    def _get_default_payment_method(self):
        return self.env.company.sale_onboarding_payment_method or 'digital_signature'

    payment_method = fields.Selection(selection_add=[
        ('digital_signature', "Electronic signature"),
        ('stripe', "Credit & Debit card (via Stripe)"),
        ('paypal', "PayPal"),
        ('other', "Other payment acquirer"),
        ('manual', "Custom payment instructions"),
    ], default=_get_default_payment_method)
    #

    def _set_payment_acquirer_onboarding_step_done(self):
        """ Override. """
        self.env.company.sudo().set_onboarding_step_done('sale_onboarding_order_confirmation_state')

    def add_payment_methods(self, *args, **kwargs):
        self.env.company.sale_onboarding_payment_method = self.payment_method
        if self.payment_method == 'digital_signature':
            self.env.company.portal_confirmation_sign = True
        if self.payment_method in ('paypal', 'stripe', 'other', 'manual'):
            self.env.company.portal_confirmation_pay = True

        return super(PaymentWizard, self).add_payment_methods(*args, **kwargs)

    def _start_stripe_onboarding(self):
        """ Override of payment to set the sale menu as start menu of the payment onboarding. """
        menu_id = self.env.ref('sale.sale_menu_root').id
        return self.env.company._run_payment_onboarding_step(menu_id)
