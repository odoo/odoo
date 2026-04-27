# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    @api.depends('res_model', 'res_id')
    def _compute_warning_message(self):
        subscription_wizard = self.env['payment.link.wizard']
        for wizard in self:
            if wizard.res_model != 'sale.order':
                continue
            order = self.env['sale.order'].browse(wizard.res_id)
            if order.subscription_state == '5_renewed':
                wizard.warning_message = _("You cannot generate a payment link for a renewed subscription")
                subscription_wizard |= wizard
        super(PaymentLinkWizard, self - subscription_wizard)._compute_warning_message()
