# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class DPOController(http.Controller):
    _return_url = '/payment/dpo/return'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def dpo_return_from_checkout(self, **data):
        """ Process the payment data sent by DPO after redirection.

        :param dict data: The payment data.
        """
        _logger.info("Handling redirection from DPO with data:\n%s", pprint.pformat(data))
        self._verify_and_process(data)

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @staticmethod
    def _verify_and_process(data):
        """ Verify and process the payment data sent by DPO.

        :param dict data: The payment data.
        :return: None
        """
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('dpo', data)
        if not tx_sudo:
            return

        try:
            # Verify the payment data.
            payload = (
                f'<?xml version="1.0" encoding="utf-8"?>'
                f'<API3G>'
                f'<CompanyToken>{tx_sudo.provider_id.dpo_company_token}</CompanyToken>'
                f'<Request>verifyToken</Request>'
                f'<TransactionToken>{data.get("TransID")}</TransactionToken>'
                f'</API3G>'
            )
            verified_data = tx_sudo._send_api_request('POST', '', data=payload)
        except ValidationError:
            _logger.error("Unable to verify the payment data.")
        else:
            data.update(verified_data)
            tx_sudo._process('dpo', data)
