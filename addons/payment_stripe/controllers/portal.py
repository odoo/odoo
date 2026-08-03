# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment_stripe import const as stripe_const


class PaymentPortal(payment_portal.PaymentPortal):
    @staticmethod
    def _validate_transaction_kwargs(kwargs, additional_allowed_keys=()):
        payment_portal.PaymentPortal._validate_transaction_kwargs(
            kwargs, additional_allowed_keys=(*additional_allowed_keys, "payment_method_type")
        )

    def _create_transaction(
        self, provider_id, payment_method_id, *args, payment_method_type=None, **kwargs
    ):
        """Override of `payment` to resolve and set the real payment method.

        Express checkout transactions are created before Stripe confirms the payment, so the
        actual payment method is not known yet when the button is rendered. The `paymentmethod`
        event however already provides it; use it to resolve the real payment method to set on
        the transaction.

        :param int provider_id: The provider of the payment method, as a `payment.provider` id.
        :param int|None payment_method_id: The payment method, as a `payment.method` id. Not set
                                           yet for express checkout transactions.
        :param str payment_method_type: The type of the payment method, as provided by Stripe's
                                        `paymentmethod` event.
        :return: The sudoed transaction that was created.
        :rtype: payment.transaction
        :raise UserError: If the payment method type cannot be resolved to a supported payment
                          method.
        """
        provider_sudo = self.env["payment.provider"].sudo().browse(provider_id)
        if provider_sudo.code == "stripe" and payment_method_type:
            payment_method_sudo = provider_sudo._get_pm_from_code(
                payment_method_type, mapping=stripe_const.PAYMENT_METHODS_MAPPING
            )
            if not payment_method_sudo:
                raise UserError(
                    self.env._(
                        "The payment method type '%s' is not supported.", payment_method_type
                    )
                )
            payment_method_id = payment_method_sudo.id
        return super()._create_transaction(provider_id, payment_method_id, *args, **kwargs)
