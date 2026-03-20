# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class AuthorizeController(http.Controller):

    @http.route('/payment/authorize/payment', type='jsonrpc', auth='public')
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
            raise ValidationError(_("Received tampered payment request data."))

        # Send the payment request to Authorize.Net.
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        response_content = tx_sudo._authorize_create_transaction_request(opaque_data)

        # Handle the payment request response
        _logger.info(
            "Payment request response for transaction %s:\n%s",
            reference, pprint.pformat(response_content)
        )
        tx_sudo._process('authorize', {'response': response_content})
