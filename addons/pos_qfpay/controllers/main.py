import json
import logging

from odoo.http import Controller, Response, request, route

_logger = logging.getLogger(__name__)


class QFPayNotificationController(Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @route(
        "/qfpay/notify",
        type="http",
        auth="receiver",
        receiver="pos.payment.method:_receiver_for_qfpay_notification",
        receiver_event="qfpay_terminal",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def qfpay_notify(self, **kwargs):
        """Receive a QFPay asynchronous payment/refund notification, admitted
        against the method its trade number names."""
        qfpay_pm_sudo = request.admission.subject
        extra = request.admission.extra
        data = extra["data"]
        _logger.info("Received QFPay notification: %s", data)
        pos_session_sudo = request.env["pos.session"].sudo().browse(extra["session_id"])
        qfpay_pm_sudo.qfpay_latest_response = json.dumps(data)
        qfpay_pm_sudo._qfpay_handle_webhook(
            pos_session_sudo.config_id, data, extra["payment_uuid"]
        )
        return Response("SUCCESS", status=200)
