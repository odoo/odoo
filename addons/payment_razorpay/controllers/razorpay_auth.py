# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, exceptions, fields, http
from odoo.addons.iap.tools import iap_tools
from odoo.http import request
from datetime import timedelta

from werkzeug.exceptions import Forbidden
from werkzeug.urls import url_join
from werkzeug.utils import redirect


_logger = logging.getLogger(__name__)


class RazorpayController(http.Controller):
    def _get_razorpay_payment_provider(self, state):
        """ To search the razorpay provider
        :return: The razorpay provider
        :rtype: recordset of `payment.provider`
        """
        return request.env['payment.provider'].sudo().search([('code', '=', 'razorpay'), ('razorpay_authorization_state', '=', state)], limit=1)

    @http.route('/payment/razorpay/oauth/callback', type='http', auth='user')
    def razorpay_callback(self, **data):
        """ Razorpay OAuth2 Callback Endpoint.
        This HTTP route handles the callback from Razorpay during the OAuth2 authorization process.
        It expects parameters such as 'code' and 'state'. If the 'code' is present, it redirects the
        user to the authorization URL. If 'code' is not present, it redirects the user to their
        base URL.
        :param dict data: The callback data containing 'code' and 'state'.
        :return: A redirection to the appropriate URL.
        :rtype: werkzeug.wrappers.response.Response
        """
        state = data.get('state')
        if not state:
            _logger.error('Razorpay: oauth callback without state.')
            raise Forbidden()
        razorpay_provider = self._get_razorpay_payment_provider(state)
        if not razorpay_provider:
            _logger.warning('Razorpay: not find any razorpay payment provider with state %s', state)
            raise Forbidden()
        code = data.get('code')
        is_successful = False

        if code:
            dbuuid = request.env['ir.config_parameter'].sudo().get_param('database.uuid')
            request_url = url_join(razorpay_provider._get_razorpay_oauth_url(), '/api/razorpay/1/get_access_token')
            try:
                params = {
                    'dbuuid': dbuuid,
                    'code': data.get('code'),
                }
                response = iap_tools.iap_jsonrpc(request_url, params=params, timeout=60)
                if 'access_token' in response:
                    is_successful = True
                    razorpay_provider.sudo().write({**self._get_razorpay_provider_vals(response), 'razorpay_key_secret': dbuuid})
            except exceptions.AccessError:
                raise exceptions.UserError(
                    _('Something went wrong during your token generation.')
                )
            try:
                razorpay_provider.sudo().action_razorpay_create_and_update_webhook()
            except exceptions.UserError as e:
                _logger.warning("Error on creating webhook %s", str(e))
        return self._get_payment_provider_web_url(razorpay_provider, is_successful)

    def _get_payment_provider_web_url(self, razorpay_provider, is_successful=True):
        """ Get the redirect URL for the payment provider based on the success status.
        :param razorpay_provider: The payment provider recordset.
        :type razorpay_provider: recordset of `payment.provider`
        :param is_successful: A flag indicating whether the operation is successful or not.
        :type is_successful: bool
        :return: The redirect URL for the payment provider.
        :rtype: str
        """
        view_ref = is_successful and 'payment.action_payment_provider' or 'payment_razorpay.action_payment_provider_onboarding_using_key'
        redirect_url = f'/web#model={razorpay_provider._name}&id={razorpay_provider.id}&action={request.env.ref(view_ref).id}&view_type=form'

        return redirect(redirect_url)

    def _get_razorpay_provider_vals(self, data):
        """ Create a vals
        :return: The razorpay provider
        :rtype: recordset of `payment.provider
        """
        expires_in = fields.Datetime.now() + timedelta(seconds=int(data.get('expires_in')))
        return {
            'razorpay_access_token': data.get('access_token'),
            'razorpay_public_token': data.get('public_token'),
            'razorpay_access_token_expiration': expires_in,
            'razorpay_refresh_token': data.get('refresh_token'),
            'razorpay_account_id': data.get('razorpay_account_id'),
            # Remove old connect method data
            'razorpay_key_id': False,
            'razorpay_key_secret': False,
            'razorpay_webhook_secret': False,
        }
