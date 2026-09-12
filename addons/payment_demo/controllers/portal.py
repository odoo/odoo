# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError

from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):
    def _create_transaction(
        self,
        provider_id,
        payment_method_id,
        token_id,
        amount,
        currency_id,
        partner_id,
        *args,
        **kwargs,
    ):
        provider_sudo = self.env["payment.provider"].sudo().browse(provider_id)
        if provider_sudo.code == "demo":
            if provider_sudo not in self.env["payment.provider"].sudo()._find_available_providers(
                provider_sudo.company_id.id, partner_id, amount
            ):
                raise ValidationError(
                    self.env._("Provider %s is not properly configured.", provider_sudo.name)
                )
            # The real payment method is not known yet when the express checkout button is
            # rendered; resolve it now instead of relying on a generic placeholder.
            payment_method_sudo = provider_sudo._get_pm_from_code("demo")
            if payment_method_sudo:
                payment_method_id = payment_method_sudo.id
        return super()._create_transaction(
            provider_id,
            payment_method_id,
            token_id,
            amount,
            currency_id,
            partner_id,
            *args,
            **kwargs,
        )
