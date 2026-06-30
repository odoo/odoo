# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    stripe_payment_method = fields.Char(string="Stripe Payment Method ID", readonly=True)
    stripe_mandate = fields.Char(string="Stripe Mandate", readonly=True)

    def _stripe_sca_migrate_customer(self):
        """ Migrate a token from the old implementation of Stripe to the SCA-compliant one.

        In the old implementation, it was possible to create a Charge by giving only the customer id
        and let Stripe use the default source (= default payment method). Stripe now requires to
        specify the payment method for each new PaymentIntent. To do so, we fetch the payment method
        associated to a customer and save its id on the token.
        This migration happens once per token created with the old implementation.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

        # Fetch the available payment method of type 'card' for the given customer
        response_content = self.provider_id._send_api_request(
            'GET',
            'payment_methods',
            data={
                'customer': self.provider_ref,
                'type': 'card',
                'limit': 1,  # A new customer is created for each new token. Never > 1 card.
            },
        )

        # Store the payment method ID on the token
        payment_methods = response_content.get('data', [])
        payment_method_id = payment_methods and payment_methods[0].get('id')
        if not payment_method_id:
            raise ValidationError(_("Unable to convert payment token to new API."))
        self.stripe_payment_method = payment_method_id
        _logger.info("converted token with id %s to new API", self.id)
