# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class AlipayController(http.Controller):
    _return_url = '/payment/alipay/return'
    _notify_url = '/payment/alipay/notify'

    @http.route(_return_url, type='http', auth="public", methods=['GET'])
    def alipay_return_from_redirect(self, **data):
        """ Alipay return """
        _logger.info("received Alipay return data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_feedback_data('alipay', data)
        return request.redirect('/payment/status')

    @http.route(_notify_url, type='http', auth='public', methods=['POST'], csrf=False)
    def alipay_notify(self, **post):
        """ Alipay Notify """
        _logger.info("received Alipay notification data:\n%s", pprint.pformat(post))
        self._alipay_validate_notification(**post)
        request.env['payment.transaction'].sudo()._handle_feedback_data('alipay', post)
        return 'success'  # Return 'success' to stop receiving notifications for this tx

    def _alipay_validate_notification(self, **post):
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'alipay', post
        )
        if not tx_sudo:
            raise ValidationError(
                "Alipay: " + _(
                    "Received notification data with unknown reference:\n%s", pprint.pformat(post)
                )
            )

        # Ensure that the notification was sent by Alipay
        # See https://global.alipay.com/docs/ac/wap/async
        acquirer_sudo = tx_sudo.acquirer_id
        val = {
            'service': 'notify_verify',
            'partner': acquirer_sudo.alipay_merchant_partner_id,
            'notify_id': post['notify_id']
        }
        response = requests.post(acquirer_sudo._alipay_get_api_url(), val, timeout=60)
        response.raise_for_status()
        if response.text != 'true':
            raise ValidationError(
                "Alipay: " + _(
                    "Received notification data not acknowledged by Alipay:\n%s",
                    pprint.pformat(post)
                )
            )
