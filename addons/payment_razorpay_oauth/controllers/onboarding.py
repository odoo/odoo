# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from datetime import timedelta
from urllib.parse import urlencode

from werkzeug.exceptions import Forbidden

from odoo import _, fields
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route


_logger = logging.getLogger(__name__)


class RazorpayController(Controller):

    OAUTH_RETURN_URL = '/payment/razorpay/oauth/return'

    @route(OAUTH_RETURN_URL, type='http', auth='user', methods=['GET'], website=True)
    def razorpay_return_from_authorization(self, **data):
        """ Exchange the authorization code for an access token and redirect to the provider form.

        :param dict data: The authorization code received from Razorpay, in addition to the provided
                          provider id and CSRF token that were sent back by the proxy.
        :raise Forbidden: If the received CSRF token cannot be verified.
        :raise ValidationError: If the provider id does not match any Razorpay provider.
        :return: Redirect to the payment provider form.
        """
        _logger.info("Returning from authorization with data:\n%s", pprint.pformat(data))

        # Retrieve the Razorpay data and Odoo metadata from the redirect data.
        provider_id = int(data['provider_id'])
        authorization_code = data.get('authorization_code')
        csrf_token = data['csrf_token']
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        if not provider_sudo or provider_sudo.code != 'razorpay':
            raise ValidationError(_("Could not find Razorpay provider with id %s", provider_sudo))

        # Verify the CSRF token.
        if not request.validate_csrf(csrf_token):
            _logger.warning("CSRF token verification failed.")
            raise Forbidden()

        # Request and set the OAuth tokens on the provider.
        action = request.env.ref('payment.action_payment_provider')
        url_params = {
            'model': provider_sudo._name,
            'id': provider_sudo.id,
            'action': action.id,
            'view_type': 'form',
        }
        redirect_url = f'/web#{urlencode(url_params)}'  # TODO: change to /odoo in saas-17.2!
        if not authorization_code: # The user cancelled the authorization.
            return request.redirect(redirect_url)
        try:
            response_content = provider_sudo._razorpay_make_proxy_request(
                '/get_access_token', payload={'authorization_code': authorization_code}
            )
        except ValidationError as e:
            return request.render(
                'payment_razorpay_oauth.authorization_error',
                qcontext={'error_message': str(e), 'provider_url': redirect_url},
            )
        expires_in = fields.Datetime.now() + timedelta(seconds=int(response_content['expires_in']))
        provider_sudo.write({
            # Reset the classical API key fields.
            'razorpay_key_id': None,
            'razorpay_key_secret': None,
            'razorpay_webhook_secret': None,
            # Set the new OAuth fields.
            'razorpay_account_id': response_content['razorpay_account_id'],
            'razorpay_public_token': response_content['public_token'],
            'razorpay_refresh_token': response_content['refresh_token'],
            'razorpay_access_token': response_content['access_token'],
            'razorpay_access_token_expiry': expires_in,
            # Enable the provider.
            'state': 'enabled',
            'is_published': True,
        })
        try:
            provider_sudo.action_razorpay_create_webhook()
        except ValidationError as error:
            _logger.warning(error)
        return request.redirect(redirect_url)
