import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import SUPERUSER_ID, _
from odoo.http import Controller, request, route
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class GelatoController(Controller):
    _webhook_url = "/gelato/webhook"

    @route(_webhook_url, type="http", methods=["POST"], auth="public", csrf=False)
    def gelato_webhook(self):
        event_data = request.get_json_data()
        _logger.info(
            "Webhook notification received from Gelato:\n%s", pprint.pformat(event_data)
        )

        _debug.pipeline(
            "gelato_webhook",
            event=event_data["event"] if isinstance(event_data, dict) else "malformed",
        )
        if event_data["event"] == "order_status_updated":
            order_id = int(event_data["orderReferenceId"])
            order_sudo = request.env["sale.order"].sudo().browse(order_id).exists()
            if not order_sudo:
                _debug.logic("gelato_webhook_unknown_order", order=order_id)
                request.env["inbound.access.log"]._record_unknown_caller(
                    "sale.order",
                    f"Gelato order {order_id}",
                    request.httprequest.remote_addr,
                    user_agent=request.httprequest.headers.get("User-Agent"),
                    status_code=403,
                )
                return request.prepare_response("", status=403)
            received_signature = request.httprequest.headers.get("signature", "")
            company_sudo = order_sudo.company_id.sudo()
            receiver = request.env["integration.receiver"]._for_record(
                company_sudo,
                _("%(company)s Gelato order updates", company=company_sudo.name),
                purpose="gelato_webhook",
            )
            if not receiver._admit_checked_request(
                lambda: self._check_notification_signature(
                    received_signature, order_sudo
                ),
                event_type="gelato_order_status_updated",
            ):
                raise Forbidden

            fulfillment_status = event_data.get("fulfillmentStatus")
            if fulfillment_status == "failed":
                log_message = _(
                    "Gelato could not proceed with the fulfillment of order %(order_reference)s:"
                    " %(gelato_message)s",
                    order_reference=order_sudo.display_name,
                    gelato_message=event_data["comment"],
                )
                order_sudo.message_post(
                    body=log_message, author_id=request.env.ref("base.partner_root").id
                )
            elif fulfillment_status == "canceled":
                order_sudo.with_user(SUPERUSER_ID)._action_cancel()

                order_sudo.line_ids.currency_id  # noqa: B018  warms the cache: the flush cannot read it under access rights

                log_message = _(
                    "Gelato has canceled order %(reference)s.",
                    reference=order_sudo.display_name,
                )
                order_sudo.message_post(
                    body=log_message, author_id=request.env.ref("base.partner_root").id
                )
            elif fulfillment_status == "in_transit":
                tracking_data = self._extract_tracking_data(
                    item_data=event_data["items"]
                )
                order_sudo.with_context(
                    {"tracking_data": tracking_data}
                ).message_post_with_source(
                    source_ref=request.env.ref("sale_gelato.order_status_update"),
                    subtype_xmlid="mail.mt_comment",
                    author_id=request.env.ref("base.partner_root").id,
                )
            elif fulfillment_status == "delivered":
                order_sudo.with_context(
                    {"order_delivered": True}
                ).message_post_with_source(
                    source_ref=request.env.ref("sale_gelato.order_status_update"),
                    subtype_xmlid="mail.mt_comment",
                    author_id=request.env.ref("base.partner_root").id,
                )
            elif fulfillment_status == "returned":
                log_message = _(
                    "Gelato has returned order %(reference)s.",
                    reference=order_sudo.display_name,
                )
                order_sudo.message_post(
                    body=log_message, author_id=request.env.ref("base.partner_root").id
                )
        return request.prepare_json_response("")

    @staticmethod
    def _check_notification_signature(received_signature, order_sudo):
        company_sudo = order_sudo.company_id.sudo()
        expected_signature = company_sudo.gelato_webhook_secret
        if not expected_signature:
            _debug.logic("gelato_signature_missing", company=company_sudo)
            _logger.warning(
                "gelato_webhook_secret not set for this company %s (id: %s)",
                company_sudo.name,
                company_sudo.id,
            )
            raise Forbidden

        if not hmac.compare_digest(received_signature, expected_signature):
            _debug.logic("gelato_signature_invalid", order=order_sudo)
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden

    @staticmethod
    def _extract_tracking_data(item_data):
        tracking_data = {}
        for i in item_data:
            for fulfilment_data in i["fulfillments"]:
                tracking_data.setdefault(
                    fulfilment_data["trackingUrl"], fulfilment_data["trackingCode"]
                )
        return tracking_data
