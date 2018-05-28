from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Step is marked as done if one payment module is installed or
    # `custom` payment has been changed or `skip this step` has been clicked
    payment_acquirer_onboarding_done = fields.Boolean('Payment acquirer onboarding done', default=False)

    @api.model
    def action_open_payment_onboarding_payment_acquirer(self):
        """ Called by onboarding panel above the customer invoice list."""
        action = self.env.ref('payment.action_open_payment_onboarding_payment_acquirer_wizard').read()[0]
        return action
