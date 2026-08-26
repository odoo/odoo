import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayWayController(http.Controller):

    @http.route('/pos/payway/webhook', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self):

        try:
            data = request.get_json_data()
            channel_name = 'pos.order.payment.payway.' + data['tran_id']

            # Send notification from backend
            request.env['bus.bus'].sudo()._sendone(
                channel_name,
                'notification',
                {
                    **data,
                    "channel_name": channel_name
                },
            )

        except Exception:
            _logger.exception("Unable to handle the webhook data.")

        return "OK"
