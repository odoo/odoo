# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError


class PaymentToken(models.Model):

    _inherit = 'payment.token'

    adyen_shopper_reference = fields.Char(
        string="Shopper Reference", help="The unique reference of the partner owning this token",
        readonly=True)

    #=== BUSINESS METHODS ===#

    def _handle_deactivation_request(self):
        """ Request Adyen to remove stored payment details of this token.

        Note: self.ensure_one()

        :return: None
        """
        if self.acquirer_id.provider != 'adyen':
            return super()._handle_deactivation_request()

        data = {
            'merchantAccount': self.acquirer_id.adyen_merchant_account,
            'shopperReference': self.adyen_shopper_reference,
            'recurringDetailReference': self.acquirer_ref,
        }
        try:
            self.acquirer_id._adyen_make_request(
                base_url=self.acquirer_id.adyen_recurring_api_url,
                endpoint_key='disable',
                payload=data,
                method='POST'
            )
        except ValidationError:
            pass  # Deactivating the token in Odoo comes before removing it from Adyen

    def _handle_activation_request(self):
        """ Raise an error informing the user that tokens managed by Adyen cannot be restored.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the token is managed by Adyen
        """
        if self.acquirer_id.provider != 'adyen':
            return super()._handle_activation_request()

        raise UserError(_("Saved payment methods cannot be restored once they have been deleted."))
