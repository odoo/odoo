# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import secrets
from urllib.parse import urlencode

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from odoo.addons.payment_paypal import const

_logger = logging.getLogger(__name__)


class PaypalOnboardingController(Controller):
    _oauth_init_url = "/payment/paypal/init_onboarding"
    _oauth_return_url = "/payment/paypal/oauth/return"

    @route(_oauth_init_url, type="jsonrpc", auth="user")
    def init_onboarding(self, provider_id):

        provider = request.env["payment.provider"].browse(provider_id)
        if not provider.exists():
            return {"error": _("Provider not found.")}

        csrf_state = secrets.token_urlsafe(32)
        request.session["paypal_onboarding_state"] = csrf_state
        request.session["paypal_onboarding_provider_id"] = provider.id

        params = {
            "partnerId": const.PARTNER_CREDENTIALS["partner_id"],
            "product": "ppcp",
            "secondaryProducts": "payment_methods,advanced_vaulting",
            "capabilities": "apple_pay,google_pay,paypal_wallet_vaulting_advanced",
            "features": "payment,refund,access_merchant_information,billing_agreement,vault",
            "integrationType": "FO",
            "partnerClientId": const.PARTNER_CREDENTIALS["partner_client_id"],
            "partnerLogoUrl": f"{provider.get_base_url()}{'/web/static/img/odoo_logo.svg'}",
            "displayMode": "minibrowser",
            "sellerNonce": provider.paypal_seller_nonce,
        }

        if provider.is_live:
            paypal_base_url = "https://www.paypal.com"
        else:
            paypal_base_url = "https://www.sandbox.paypal.com"

        url_endpoint = f"{paypal_base_url}/bizsignup/partner/entry"
        paypal_url = f"{url_endpoint}?{urlencode(params)}"

        return {"csrf_state": csrf_state, "paypal_url": paypal_url}

    @route(_oauth_return_url, type="http", auth="user", methods=["GET"], website=True)
    def paypal_return_from_authorization(self, **data):
        """Exchange the authorization code and shared id for an access token, retrieve seller
        credentials, and complete the PayPal onboarding process.

        :param dict data: The authorization code and the shared id received from PayPal.
        :raise Validation Error: If an unexpected error occurs during API communication or when
                                writing the credentials to the database.
        :return: Redirect to the payment provider form.
        """
        _logger.info("Processing onboarding with data:\n%s", pprint.pformat(data))

        auth_code = data.get("authCode")
        shared_id = data.get("sharedId")
        returned_state = data.get("state")

        expected_state = request.session.pop("paypal_onboarding_state", None)
        if (
            not expected_state
            or not returned_state
            or not secrets.compare_digest(expected_state, returned_state)
        ):
            raise ValidationError(
                _(
                    "Invalid or expired session state. Please restart the onboarding process from"
                    " your payment provider settings."
                )
            )

        if not auth_code or not shared_id:
            raise ValidationError(
                _("Something went wrong with PayPal onboarding: Missing authCode or sharedId.")
            )

        provider_id = request.session.pop("paypal_onboarding_provider_id", None)
        if not provider_id:
            raise ValidationError(_("Onboarding session not found. Please restart the process."))
        provider = request.env["payment.provider"].sudo().browse(provider_id)
        if not provider.exists():
            raise ValidationError(_("Could not find Paypal provider."))

        onboarding_token = provider._paypal_request_onboarding_token(auth_code, shared_id)
        response_content = provider._send_api_request(
            "GET",
            f"/v1/customer/partners/{const.PARTNER_CREDENTIALS['partner_id']}/merchant-integrations/credentials",
            paypal_onboarding_access_token=onboarding_token,
        )

        provider.write({
            "paypal_client_id": response_content["client_id"],
            "paypal_client_secret": response_content["client_secret"],
            "paypal_account_id": response_content["payer_id"],
            "paypal_is_isu_onboarded": True,
        })
        provider._paypal_check_onboarding_status()
        try:
            provider.action_paypal_create_webhook()
        except ValidationError as e:
            _logger.warning(e)

        redirect_url = f"/odoo/payment-providers/{provider.id}"
        return request.redirect(redirect_url)
