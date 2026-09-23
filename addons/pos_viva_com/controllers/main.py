import logging

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosVivaComController(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/pos_viva_com/notification",
        type="http",
        auth="receiver",
        receiver="pos.payment.method:_receiver_for_viva_com_notification",
        receiver_event="viva_com_terminal",
        csrf=False,
        readonly=False,
        typed=True,
    )
    def notification(self, company_id: int, token: str):
        _logger.info("notification received from Viva.com")
        payment_method_sudo = request.admission.subject
        if request.httprequest.data:
            data = request.get_json_data()
            terminal_id = data.get("EventData", {}).get("TerminalId", "")
            event_type = data.get("EventTypeId")
            data_webhook = data.get("EventData", {})
            if event_type != 1796:  # Transaction Payment Created
                _logger.warning(
                    'received a message with an unknown event type "%s". See https://developer.viva.com/webhooks-for-payments/#webhook-events.',
                    event_type,
                )
            elif terminal_id:
                payment_method_sudo = (
                    request.env["pos.payment.method"]
                    .sudo()
                    .search([("viva_com_terminal_id", "=", terminal_id)], limit=1)
                )
                payment_method_sudo._notify_session_status(data_webhook)
            else:
                _logger.error(
                    _(
                        "received a message for a terminal not registered in Odoo: %s",
                        terminal_id,
                    )
                )
        return request.prepare_json_response(
            {"Key": request.admission.subject.viva_com_webhook_verification_key}
        )
