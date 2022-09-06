# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    def _get_additional_link_values(self):
        res = super()._get_additional_link_values()
        if self.res_model != 'account.move':
            return res

        # Invoice-related fields are retrieved in the controller.
        return {
            'invoice_id': self.res_id,
        }
