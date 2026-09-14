import logging

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class PosVivaComController(http.Controller):
    @http.route(
        "/pos_viva_com/notification",
        type="http",
        auth="none",
        csrf=False,
        readonly=False,
    )
    def notification(self, company_id, token):
        _logger.info("notification received from Viva.com")

        viva_payment_methods = (
            request.env["pos.payment.method"]
            .sudo()
            .search(
                [
                    ("use_payment_terminal", "=", "viva_com"),
                    ("company_id.id", "=", int(company_id)),
                ]
            )
        )
        payment_method_sudo = next(
            (
                pm
                for pm in viva_payment_methods
                if consteq(pm.viva_com_webhook_verification_key, token)
            ),
            None,
        )

        if payment_method_sudo:

            def check_token():
                if not consteq(
                    payment_method_sudo.viva_com_webhook_verification_key, token
                ):
                    raise Forbidden

            receiver = request.env["integration.receiver"]._for_record(
                payment_method_sudo, f"{payment_method_sudo.name} notifications"
            )
            if not receiver._admit_checked_request(
                check_token, event_type="viva_com_terminal"
            ):
                return None
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
                {"Key": payment_method_sudo.viva_com_webhook_verification_key}
            )
        else:
            _logger.error(
                _("received a message for a pos payment provider not registered.")
            )
            request.env["inbound.access.log"]._record_unknown_caller(
                "pos.payment.method",
                f"viva.com company {company_id}",
                request.httprequest.remote_addr,
                user_agent=request.httprequest.headers.get("User-Agent"),
            )
            return None
