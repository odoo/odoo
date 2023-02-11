# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    def _handle_reactivation_request(self):
        """ Override of payment to raise an error informing that Ogone tokens cannot be restored.

        More specifically, permanents tokens are never deleted in Ogone's backend but we don't
        distinguish them from temporary tokens which are archived at creation time. So we simply
        block the reactivation of every token.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the token is managed by Ogone
        """
        super()._handle_reactivation_request()
        if self.provider != 'ogone':
            return

        raise UserError(_("Saved payment methods cannot be restored once they have been archived."))
