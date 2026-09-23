import logging
import pprint

from odoo import SUPERUSER_ID, _
from odoo.http import Controller, request, route
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class GelatoController(Controller):
    _webhook_url = "/gelato/webhook"

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @route(
        _webhook_url,
        type="http",
        methods=["POST"],
        auth="receiver",
        receiver="sale.order:_receiver_for_gelato_webhook",
        receiver_event="gelato_order_status_updated",
        csrf=False,
        typed=True,
    )
    def gelato_webhook(self):
        order_sudo = request.admission.subject
        event_data = request.admission.extra["event"]
        _logger.info(
            "Webhook notification received from Gelato:\n%s", pprint.pformat(event_data)
        )
        _debug.pipeline("gelato_webhook", event=event_data["event"])
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
            tracking_data = self._extract_tracking_data(item_data=event_data["items"])
            order_sudo.with_context(
                {"tracking_data": tracking_data}
            ).message_post_with_source(
                source_ref=request.env.ref("sale_gelato.order_status_update"),
                subtype_xmlid="mail.mt_comment",
                author_id=request.env.ref("base.partner_root").id,
            )
        elif fulfillment_status == "delivered":
            order_sudo.with_context({"order_delivered": True}).message_post_with_source(
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
    def _extract_tracking_data(item_data):
        tracking_data = {}
        for i in item_data:
            for fulfilment_data in i["fulfillments"]:
                tracking_data.setdefault(
                    fulfilment_data["trackingUrl"], fulfilment_data["trackingCode"]
                )
        return tracking_data
