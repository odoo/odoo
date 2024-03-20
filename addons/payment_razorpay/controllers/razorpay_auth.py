# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from werkzeug.exceptions import Forbidden
from werkzeug.urls import url_join
from werkzeug.utils import redirect

from odoo import fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class RazorpayController(http.Controller):

    @http.route('/payment/razorpay/oauth/callback', type='http', auth='user')
    def razorpay_oauth_callback(self, **data):
        """
        Razorpay Oauth Callback Endpoint.
        This route handles the callback from Razorpay during the Oauth authorization process.
        It expects parameters like 'code' and 'state'. If 'code' is provided, it attempts to
        get an access token. If 'code' is missing, the user is redirected to the razorpay form
        view.

        :param dict data: The callback data containing 'code' and 'state'.
        :return: Redirect to the related Razorpay form view.
        :rtype: Response
        """
        state = data.get('state')
        if not state:
            _logger.error("Oauth callback without state.")
            raise Forbidden()

        razorpay_provider = request.env['payment.provider'].sudo().search([
            ('code', '=', 'razorpay'),
            ('razorpay_authorization_state', '=', state),
        ], limit=1)
        if not razorpay_provider:
            _logger.warning(
                "Can't find any Razorpay provider for the given state %s",
                state
            )
            raise Forbidden()

        action = request.env.ref('payment.action_payment_provider')
        redirect_url = '/odoo/action-%s/%s' % (action.id, int(razorpay_provider.id))
        code = data.get('code')
        if code:
            request_url = url_join(
                razorpay_provider._razorpay_get_oauth_url(), '/api/razorpay/1/get_access_token'
            )
            try:
                params = {
                    'code': code,
                }
                response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
                if 'access_token' in response:
                    expires_in = fields.Datetime.now() + timedelta(seconds=int(response['expires_in']))
                    razorpay_provider.sudo().write({
                        'razorpay_account_id': response.get('razorpay_account_id'),
                        'razorpay_access_token': response.get('access_token'),
                        'razorpay_access_token_expiration': expires_in,
                        'razorpay_public_token': response.get('public_token'),
                        'razorpay_refresh_token': response.get('refresh_token'),
                        # Reset key for oauth flow
                        'razorpay_key_id': False,
                    })
            except (AccessError, UserError) as e:
                return request.render(
                    'payment_razorpay.razorpay_authorization_error',
                    qcontext={'error_message': str(e), 'redirect_url': redirect_url},
                )
            try:
                razorpay_provider.sudo().action_razorpay_create_or_update_webhook()
            except Exception:
                _logger.exception("Unknown Error during creating the webhook.")

        return redirect(redirect_url)
