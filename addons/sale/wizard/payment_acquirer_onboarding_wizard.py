# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class PaymentWizard(models.TransientModel):
    _inherit = 'payment.acquirer.onboarding.wizard'
    _name = 'sale.payment.acquirer.onboarding.wizard'

    def _hook_on_save_onboarding_payment_acquirer(self):
        """ Override. Activate the option in sales settings. """
        self.env.user.company_id.portal_confirmation_pay = True

    def _set_payment_acquirer_onboarding_step_done(self):
        """ Override. """
        self.env.user.company_id.sale_onboarding_payment_acquirer_done = True
