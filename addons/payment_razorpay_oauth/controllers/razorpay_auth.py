# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta
from werkzeug.exceptions import Forbidden
from werkzeug.utils import redirect

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.http import Controller, route, request

_logger = logging.getLogger(__name__)


class RazorpayController(Controller):

    @route('/payment/razorpay/oauth/callback', type='http', auth='user')
    def razorpay_oauth_callback(self, **data):
        """
        Handle the callback from Razorpay during OAuth authorization.
        This method is triggered when Razorpay redirects the user back to your site after they
        authorize the app.It uses the provided 'code' and 'state' parameters to get an access token
        from Razorpay and updates the payment provider's details. If there's an issue
        (like a missing code), the user is redirected back to the Razorpay form view with an
        error message.

        :param dict data: The callback data containing 'code' and 'state'.
        :return: Redirect to the related Razorpay form view.
        :rtype: Response.
        """
        state = data.get('state')
        code = data.get('code')
        if not state or not code:
            _logger.warning("Invalid State or Code for Razorpay provider")
            raise Forbidden()

        razorpay_provider_id = int(state.split('-')[0])
        razorpay_provider = request.env['payment.provider'].sudo().browse(razorpay_provider_id)
        action = request.env.ref('payment.action_payment_provider')
        redirect_url = f'/web#model={razorpay_provider._name}&id={razorpay_provider.id}&action={action.id}&view_type=form'
        try:
            response = razorpay_provider._razorpay_make_proxy_request(
                '/api/razorpay/1/get_access_token',
                params={'code': code},
            )
        except ValidationError as e:
            return request.render(
                'payment_razorpay_oauth.razorpay_redirect_error_template',
                qcontext={
                    'error_message': str(e),
                    'redirect_url': redirect_url,
                },
            )
        expires_in = fields.Datetime.now() + timedelta(seconds=int(response['expires_in']))
        razorpay_provider.sudo().write({
            'razorpay_account_id': response['razorpay_account_id'],
            'razorpay_access_token': response['access_token'],
            'razorpay_access_token_expiration': expires_in,
            'razorpay_public_token': response['public_token'],
            'razorpay_refresh_token': response['refresh_token'],
            'state': 'enabled',
            # Reset key for oauth flow
            'razorpay_key_id': False,
        })
        try:
            razorpay_provider.sudo().action_razorpay_create_webhook()
        except ValidationError as e:
            _logger.warning("Error while creating the webhook: '%s'", e)

        return redirect(redirect_url)
