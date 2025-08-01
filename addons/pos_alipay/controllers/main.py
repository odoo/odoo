# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import pprint
import json

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosAlipayController(http.Controller):
    @http.route('/pos_alipay/notify', type='http', methods=['POST'], auth='none')
    def notification(self):
        data = json.loads(request.httprequest.data)

        # ignore if it's not a payment result notification
        if data.get('notifyType') != 'PAYMENT_RESULT':
            return

        _logger.info('notificatiopn received from alipay:\n%s', pprint.pformat(data))
        # Example data:
        # {
        #     "notifyType": "PAYMENT_RESULT",
        #     "result": {
        #         "resultCode": "SUCCESS",
        #         "resultStatus": "S",
        #         "resultMessage": "success"
        #     },
        #     "paymentRequestId": "2020010123456789XXXX",
        #     "paymentId": "2020010123456789XXXX",
        #     "paymentAmount": {
        #         "value": "8000",
        #         "currency": "EUR"
        #     },
        #     "paymentCreateTime": "2020-01-01T12:01:00+08:30",
        #     "paymentTime": "2020-01-01T12:01:01+08:30"
        # }
        if data['result']['resultStatus'] == 'S':
            pos_session_id, payment_method_id = int(data['paymentRequestId'].split("_")[1]), int(data['paymentRequestId'].split("_")[2])
            pos_session_sudo = request.env['pos.session'].sudo().browse(pos_session_id)
            payment_method_sudo = request.env['pos.payment.method'].sudo().browse(payment_method_id)
            if pos_session_sudo:
                request.env["bus.bus"].sudo()._sendone(pos_session_sudo._get_bus_channel_name(), "ALIPAY_LATEST_RESPONSE", pos_session_sudo.config_id.id)
                payment_method_sudo.alipay_latest_response = json.dumps(data)
                data = {
                    "result": {
                        "resultCode": "SUCCESS",
                        "resultStatus": "S",
                        "resultMessage": "success"
                    }
                }
                return request.make_json_response(data, status=200)
        else:
            _logger.error('Alipay payment failed:\n%s', pprint.pformat(data))
            # return response json
            data = {
                "result": {
                    "resultCode": "FAIL",
                    "resultStatus": "F",
                    "resultMessage": "failed"
                }
            }
            return request.make_json_response(data, status=200)
