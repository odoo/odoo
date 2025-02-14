# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class DPOController(http.Controller):
    _return_url = '/payment/dpo/return'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def dpo_return_from_checkout(self, **data):
        """ Process the notification data sent by DPO after redirection.
        """
        _logger.info("Handling redirection from DPO with data:\n%s", pprint.pformat(data))

        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'dpo', data
        )
        transaction_result = self._dpo_verify_transaction_token(data.get('TransID'), tx_sudo)
        data.update(transaction_result)

        # Handle the notification data.
        tx_sudo._handle_notification_data('dpo', data)

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    def _dpo_verify_transaction_token(self, transaction_token, tx_sudo):
        """ Verify the transaction token and return the response data.
            This method is used to validate the payment.

        :return: The transaction payments data.
        :rtype: dict
        """
        payload = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <API3G>
                <CompanyToken>{tx_sudo.provider_id.dpo_company_token}</CompanyToken>
                <Request>verifyToken</Request>
                <TransactionToken>{transaction_token}</TransactionToken>
            </API3G>
        """
        return tx_sudo.provider_id._dpo_make_request(payload=payload)
