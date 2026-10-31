# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.float_utils import float_repr

from odoo.addons.payment import utils as payment_utils


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    def _get_additional_link_values(self):
        """ Override of `payment` to add `invoice_id` to the payment link values.

        The other values related to the invoice are directly read from the invoice.

        Note: self.ensure_one()

        :return: The additional payment link values.
        :rtype: dict
        """
        res = super()._get_additional_link_values()
        if self.res_model != 'account.move':
            return res

        # Invoice-related fields are retrieved in the controller.
        return {
            'invoice_id': self.res_id,
        }

    def _get_access_token(self):
        """ Override of `payment` to include the invoice in the access token. """
        res = super()._get_access_token()
        if self.res_model != 'account.move':
            return res

        return payment_utils.generate_access_token(
            self.partner_id.id,
            float(float_repr(self.amount, self.currency_id.decimal_places)),
            self.currency_id.id,
            self.res_model,
            self.res_id,
        )
