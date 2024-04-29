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

        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from DPO with data:\n%s", pprint.pformat(data))
        self._verify_and_handle_notification_data(data)

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @staticmethod
    def _verify_and_handle_notification_data(data):
        """ Verify and process the notification data sent by DPO.

        :param dict data: The notification data.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'dpo', data
        )
        payload = (
            f'<?xml version="1.0" encoding="utf-8"?>'
            f'<API3G>'
                f'<CompanyToken>{tx_sudo.provider_id.dpo_company_token}</CompanyToken>'
                f'<Request>verifyToken</Request>'
                f'<TransactionToken>{data.get("TransID")}</TransactionToken>'
            f'</API3G>'
        )
        # Verify the notification data.
        verified_data = tx_sudo.provider_id._dpo_make_request(payload=payload)
        data.update(verified_data)

        # Handle the notification data.
        tx_sudo._handle_notification_data('dpo', data)
