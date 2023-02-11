# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class AuthorizeController(http.Controller):

    @http.route('/payment/authorize/get_acquirer_info', type='json', auth='public')
    def authorize_get_acquirer_info(self, acquirer_id):
        """ Return public information on the acquirer.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :return: Information on the acquirer, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id).exists()
        return {
            'state': acquirer_sudo.state,
            'payment_method_type': acquirer_sudo.authorize_payment_method_type,
            # The public API key solely used to identify the seller account with Authorize.Net
            'login_id': acquirer_sudo.authorize_login,
            # The public client key solely used to identify requests from the Accept.js suite
            'client_key': acquirer_sudo.authorize_client_key,
        }

    @http.route('/payment/authorize/payment', type='json', auth='public')
    def authorize_payment(self, reference, partner_id, access_token, opaque_data):
        """ Make a payment request and handle the response.

        :param str reference: The reference of the transaction
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str access_token: The access token used to verify the provided values
        :param dict opaque_data: The payment details obfuscated by Authorize.Net
        :return: None
        """
        # Check that the transaction details have not been altered
        if not payment_utils.check_access_token(access_token, reference, partner_id):
            raise ValidationError("Authorize.Net: " + _("Received tampered payment request data."))

        # Make the payment request to Authorize.Net
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        response_content = tx_sudo._authorize_create_transaction_request(opaque_data)

        # Handle the payment request response
        _logger.info("make payment response:\n%s", pprint.pformat(response_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': tx_sudo.reference, 'response': response_content}
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            'authorize', feedback_data
        )
