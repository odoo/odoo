import hashlib
import json
import logging

from werkzeug.exceptions import Forbidden

from odoo.http import Controller, Response, request, route
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class QFPayNotificationController(Controller):
    @route("/qfpay/notify", type="http", auth="public", methods=["POST"], csrf=False)
    def qfpay_notify(self, **kwargs):
        """
        Endpoint to receive QFPay asynchronous payment/refund notifications.
        Verifies signature and returns 'SUCCESS' if valid, else 400 error.
        """
        raw_body = request.httprequest.get_data()
        data = json.loads(raw_body.decode("utf-8"))

        _logger.info("Received QFPay notification: %s", data)

        # Retrieve the payment method to verify the signature
        # Be careful, at this point we have not yet verified the signature
        trade_no = data.get("orig_out_trade_no", data.get("out_trade_no"))
        try:
            [payment_uuid, session_id, pm_id] = trade_no.split("--")
        except ValueError:
            _logger.warning("QFpay invalid out_trade_no format")
            return None
        qfpay_pm_sudo = request.env["pos.payment.method"].sudo().browse(int(pm_id))
        if not qfpay_pm_sudo.exists() or not qfpay_pm_sudo.qfpay_notification_key:
            _logger.warning("QFPay payment method does not have a notification key set")
            return None

        def check_signature():
            sign_str = raw_body + qfpay_pm_sudo.qfpay_notification_key.encode()
            computed_sign = hashlib.md5(sign_str).hexdigest().upper()
            if not consteq(
                computed_sign, request.httprequest.headers.get("X-QF-SIGN") or ""
            ):
                raise Forbidden

        receiver = request.env["integration.receiver"]._for_record(
            qfpay_pm_sudo, f"{qfpay_pm_sudo.name} notifications"
        )
        if not receiver._admit_checked_request(
            check_signature, event_type="qfpay_terminal"
        ):
            _logger.warning("QFPay notification signature mismatch")
            return None

        # We have verified the signature we can trust the data
        pos_session_sudo = request.env["pos.session"].sudo().browse(int(session_id))
        qfpay_pm_sudo.qfpay_latest_response = json.dumps(data)
        qfpay_pm_sudo._qfpay_handle_webhook(
            pos_session_sudo.config_id, data, payment_uuid
        )

        return Response("SUCCESS", status=200)
