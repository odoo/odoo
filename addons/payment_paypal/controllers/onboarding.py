# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import secrets
from urllib.parse import urlencode

from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from odoo.addons.payment_paypal import const

_logger = logging.getLogger(__name__)


class PaypalOnboardingController(Controller):
    @route(const.OAUTH_INIT_ROUTE, type="jsonrpc", auth="user")
    def init_onboarding(self, provider_id):
        """Return the URLs needed to open the PayPal onboarding page in a mini browser.

        :param int provider_id: The provider being onboarded, as a `payment.provider` id
        :return: The URL of the merchant-specific onboarding page, and the URL of the partner SDK
                 that opens it
        :rtype: dict
        """
        # Generate a merchant-specific nonce to identify the OAuth values returned by PayPal
        provider = request.env["payment.provider"].browse(provider_id)
        provider.paypal_seller_nonce = secrets.token_urlsafe(32)

        # Prepare the onboarding page rendering values
        base_url = provider.get_base_url()
        action = self.env.ref("payment.action_payment_provider")
        redirect_url = f"/odoo/action-{action.id}/{provider_id}"
        params = {
            "partnerId": const.OAUTH_ODOO_PARTNER_ID,
            "partnerClientId": const.OAUTH_ODOO_CLIENT_ID,
            "product": "ppcp",
            "secondaryProducts": "payment_methods,advanced_vaulting",
            "capabilities": "paypal_wallet_vaulting_advanced",
            "features": "payment,refund,access_merchant_information,billing_agreement,vault",
            "integrationType": "FO",
            "partnerLogoUrl": f"{base_url}/web/static/img/odoo_logo.svg",
            "returnToPartnerUrl": f"{base_url}{redirect_url}",
            "displayMode": "minibrowser",
            "sellerNonce": provider.paypal_seller_nonce,
        }

        # Build the URLs of the onboarding page and of the SDK on the matching PayPal environment
        if provider.is_live:
            paypal_merchant_url = "https://www.paypal.com"
        else:
            paypal_merchant_url = "https://www.sandbox.paypal.com"
        paypal_url = f"{paypal_merchant_url}/bizsignup/partner/entry?{urlencode(params)}"
        partner_sdk_url = (
            f"{paypal_merchant_url}/webapps/merchantboarding/js/lib/lightbox/partner.js"
        )

        return {"paypal_url": paypal_url, "partner_sdk_url": partner_sdk_url}

    @route(const.OAUTH_FINALIZE_ROUTE, type="jsonrpc", auth="user")
    def finalize_onboarding(self, auth_code=None, shared_id=None, provider_id=None):
        """Exchange the authorization code and shared id to complete the PayPal onboarding process.

        :param str auth_code: The authorization code received from PayPal
        :param str shared_id: The shared id received from PayPal
        :param int provider_id: The provider being onboarded, as a `payment.provider` id
        :rtype: None
        :raise ValidationError: If PayPal did not return the OAuth values or if the credentials
                                exchange fails
        """
        if not auth_code or not shared_id:
            raise ValidationError(
                self.env._("PayPal did not return the authorization code or the shared id.")
            )

        # Exchange the authorization code for an access token
        provider = request.env["payment.provider"].browse(provider_id).exists()
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": provider.paypal_seller_nonce,
        }
        access_token = provider._send_api_request(
            "POST", "/v1/oauth2/token", data=data, paypal_onboarding_shared_id=shared_id
        ).get("access_token")
        if not access_token:
            raise ValidationError(self.env._("Failed to retrieve access token."))

        # Fetch the API credentials of the merchant account
        response_content = provider._send_api_request(
            "GET",
            f"/v1/customer/partners/{const.OAUTH_ODOO_PARTNER_ID}"
            "/merchant-integrations/credentials",
            paypal_onboarding_access_token=access_token,
        )

        # Save the credentials and the status of the merchant account
        provider.write({
            "paypal_client_id": response_content.get("client_id"),
            "paypal_client_secret": response_content.get("client_secret"),
            "paypal_account_id": response_content.get("payer_id"),
            "paypal_is_oauth_onboarded": True,
            "is_published": True,
        })
        provider._paypal_update_onboarding_status()

        # Create the webhook without blocking the onboarding if it fails
        try:
            provider.action_paypal_create_webhook()
        except ValidationError as e:
            _logger.warning(e)
