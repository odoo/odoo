# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request

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
        provider_sudo = request.env["payment.provider"].sudo().browse(provider_id)
        if provider_sudo.code == "demo" and provider_sudo not in request.env[
            "payment.provider"
        ].sudo()._get_compatible_providers(provider_sudo.company_id.id, partner_id, amount):
            raise ValidationError(_("Provider %s is not properly configured.", provider_sudo.name))
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
