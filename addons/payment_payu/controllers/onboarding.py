# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from odoo.addons.payment_payu import const

_logger = logging.getLogger(__name__)


class PayUOnboardingController(Controller):
    @route(
        const.OAUTH_RETURN_ROUTE,
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
        save_session=False,
    )
    def payu_return_from_authorization(self, **data):
        """Handle the PayU OAuth callback.

        :param dict data: The authorization code and merchant ID received from PayU, in addition to
                          the Odoo provider id and CSRF token sent back by the proxy
        :raise Forbidden: If the received CSRF token cannot be verified
        :raise ValidationError: If the provider id does not match any PayU provider
        :return: Redirect to the payment provider form
        """
        _logger.info("Returning from PayU authorization with data:\n%s", pprint.pformat(data))

        # Retrieve the PayU data and Odoo metadata from the redirect data
        merchant_id = data.get("merchant_id")
        authorization_code = data.get("auth_code")
        provider_id = int(data["provider_id"])
        csrf_token = data["csrf_token"]
        provider_sudo = self.env["payment.provider"].sudo().browse(provider_id).exists()
        if not provider_sudo or provider_sudo.code != "payu":
            raise ValidationError(
                self.env._("Could not find PayU provider with id %s", provider_sudo.id)
            )

        # Verify the CSRF token
        if not request.validate_csrf(csrf_token):
            _logger.warning("CSRF token verification failed.")
            raise Forbidden

        action = self.env.ref("payment.action_payment_provider")
        redirect_url = f"/odoo/action-{action.id}/{int(provider_sudo.id)}"
        if not authorization_code:  # The user cancelled the authorization
            return request.redirect(redirect_url)

        # Fetch the credentials using the authorization token
        proxy_payload = {
            "authorization_code": authorization_code,
            "redirect_uri": f"{const.OAUTH_URL}/redirect",
        }
        try:
            response_content = provider_sudo._send_api_request(
                "POST", "/get_access_token", json=proxy_payload, is_proxy_request=True
            )
            access_token = response_content["access_token"]
            credentials_response = provider_sudo._send_api_request(
                "GET", f"/api/v1/merchants/{merchant_id}/credential", payu_access_token=access_token
            )
        except ValidationError as error:
            return request.render(
                "payment_payu.authorization_error",
                {"error_message": str(error), "provider_url": redirect_url},
            )
        credentials = credentials_response.get("data", {}).get("credentials", {})
        provider_sudo.write({
            # Save the OAuth credentials
            "payu_key_id": credentials.get("prod_key"),
            "payu_merchant_salt": credentials.get("prod_salt"),
            # Enable the provider
            "state": "enabled",
            "is_published": True,
        })
        return request.redirect(redirect_url)
