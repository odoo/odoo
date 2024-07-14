# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class PaymentLinkWizardExternalTax(models.TransientModel):
    _inherit = "payment.link.wizard"

    @api.model
    def default_get(self, fields):
        res_id = self._context.get('active_id')
        res_model = self._context.get('active_model')

        # This ensures that taxes are up-to-date and the required information is set so the customer clicking
        # the payment link won't see an error.
        if res_id and res_model:
            self.env[res_model].browse(res_id)._get_and_set_external_taxes_on_eligible_records()

        return super().default_get(fields)
