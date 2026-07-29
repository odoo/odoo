# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from urllib.parse import urlencode

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from odoo.addons.payment_paypal import const

_logger = logging.getLogger(__name__)


class PaypalOnboardingController(Controller):
    _oauth_init_url = "/payment/paypal/init_onboarding"
    _oauth_return_url = "/payment/paypal/oauth/return"
    _oauth_error_url = "/payment/paypal/onboarding/error"

    @route(_oauth_init_url, type="jsonrpc", auth="user")
    def init_onboarding(self, provider_id):

        provider = request.env["payment.provider"].browse(provider_id)
        if not provider.exists():
            return {"error": _("Provider not found.")}

        base_url = provider._paypal_get_base_url()
        action = self.env.ref("payment.action_payment_provider")
        redirect_url = f"/odoo/action-{action.id}/{provider_id}"
        params = {
            "partnerId": const.ONBOARDING_REFERENCE["partner_id"],
            "product": "ppcp",
            "secondaryProducts": "payment_methods,advanced_vaulting",
            "capabilities": "apple_pay,google_pay,paypal_wallet_vaulting_advanced",
            "features": "payment,refund,access_merchant_information,billing_agreement,vault",
            "integrationType": "FO",
            "partnerClientId": const.ONBOARDING_REFERENCE["partner_client_id"],
            "partnerLogoUrl": f"{base_url}{'/web/static/img/odoo_logo.svg'}",
            "returnToPartnerUrl": f"{base_url}{redirect_url}",
            "sellerNonce": provider.paypal_seller_nonce,
        }

        if provider.is_live:
            paypal_merchant_url = "https://www.paypal.com"
        else:
            paypal_merchant_url = "https://www.sandbox.paypal.com"

        url_endpoint = f"{paypal_merchant_url}/bizsignup/partner/entry"
        paypal_url = f"{url_endpoint}?{urlencode(params)}"
        partner_sdk_url = (
            f"{paypal_merchant_url}/webapps/merchantboarding/js/lib/lightbox/partner.js"
        )

        return {"paypal_url": paypal_url, "partner_sdk_url": partner_sdk_url}

    @route(_oauth_return_url, type="jsonrpc", auth="user")
    def paypal_return_from_authorization(self, auth_code=None, shared_id=None, provider_id=None):
        """Exchange the authorization code and shared id to complete the PayPal onboarding process.

        :param str auth_code: The authorization code received from PayPal.
        :param str shared_id: The shared id received from PayPal.
        :return: An empty dict on success, or a dict with an `error` message on failure.
        :rtype: dict
        """
        if not auth_code or not shared_id:
            return {
                "error": _(
                    "Something went wrong with PayPal onboarding: Missing authorization code or"
                    " shared id."
                )
            }

        provider = request.env["payment.provider"].sudo().browse(provider_id)
        if not provider.exists():
            return {"error": _("Could not find Paypal provider.")}

        try:
            onboarding_token = provider._paypal_request_onboarding_token(auth_code, shared_id)
            response_content = provider._send_api_request(
                "GET",
                f"/v1/customer/partners/{const.ONBOARDING_REFERENCE['partner_id']}/merchant-integrations/credentials",
                paypal_onboarding_access_token=onboarding_token,
            )
        except ValidationError as e:
            error_params = urlencode({"error_message": str(e), "provider_id": provider.id})
            return {"error_url": f"{self._oauth_error_url}?{error_params}"}

        provider.write({
            "paypal_client_id": response_content["client_id"],
            "paypal_client_secret": response_content["client_secret"],
            "paypal_account_id": response_content["payer_id"],
            "paypal_is_oauth_onboarded": True,
            "is_published": True,
        })
        provider._paypal_check_onboarding_status()
        try:
            provider.action_paypal_create_webhook()
        except ValidationError as e:
            _logger.warning(e)

        return {}

    @route(_oauth_error_url, type="http", auth="user", website=True)
    def paypal_onboarding_error(self, error_message="", provider_id=None):
        """Render the onboarding error page after a failed credential exchange.

        :param str error_message: The reason of the failure.
        :param str provider_id: The id of the provider whose onboarding failed.
        :return: The rendered error page.
        """
        action = request.env.ref("payment.action_payment_provider")
        provider_url = f"/odoo/action-{action.id}/{provider_id}"
        return request.render(
            "payment_paypal.authorization_error",
            {"error_message": error_message, "provider_url": provider_url},
        )
