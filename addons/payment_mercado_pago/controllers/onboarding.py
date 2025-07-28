# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from datetime import timedelta

from odoo import _, fields
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class MercadoPagoController(Controller):

    OAUTH_RETURN_URL = '/payment/mercado_pago/oauth/return'

    @route(OAUTH_RETURN_URL, type='http', auth='user', methods=['GET'], website=True)
    def mercado_pago_return_from_authorization(
            self, provider_id, csrf_token=None, authorization_code=None, **data
    ):

        _logger.info("Returning from authorization with data:\n%s", pprint.pformat(data))

        provider_sudo = request.env['payment.provider'].sudo().browse(int(provider_id)).exists()
        if not provider_sudo or provider_sudo.code != 'mercado_pago':
            raise ValidationError(_(
                "Could not find Mercado Pago provider with id %s", provider_sudo
            ))

        # Verify the CSRF token.
        payment_utils.check_csrf_token(csrf_token)

        # get the access token using authorization_token
        # Request and set the OAuth tokens on the provider.
        action = request.env.ref('payment.action_payment_provider')
        redirect_url = f'/odoo/action-{action.id}/{int(provider_sudo.id)}'
        if not authorization_code:  # The user cancelled the authorization.
            return request.redirect(redirect_url)

        proxy_payload = self.env['payment.provider']._prepare_json_rpc_payload(
            {'authorization_code': authorization_code}
        )

        response_content = provider_sudo._send_api_request(
            'POST', '/get_access_token', json=proxy_payload, is_proxy_request=True,
        )

        # set the expiry date month before, so new refresh token will be retrieved using cron before
        # current access token expiration
        expires_in = (
            fields.Datetime.now()
            + timedelta(seconds=int(response_content['expires_in']))
            - timedelta(days=31)
        )
        # save values on provider
        provider_sudo.write({
            'mercado_pago_access_token': response_content['access_token'],
            'mercado_pago_refresh_token': response_content['refresh_token'],
            'mercado_pago_access_token_expiry': expires_in,
            'mercado_pago_public_key': response_content['public_key'],
        })

        return request.redirect(redirect_url)
