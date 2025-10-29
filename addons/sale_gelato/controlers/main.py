# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import SUPERUSER_ID, _
from odoo.http import Controller, request, route


_logger = logging.getLogger(__name__)


class GelatoController(Controller):
    _webhook_url = '/gelato/webhook'

    @route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def gelato_webhook(self):
        """ Process the notification data sent by Gelato to the webhook.

        See https://dashboard.gelato.com/docs/orders/order_details/#order-statuses for the event
        codes.

        :return: An empty response to acknowledge the notification.
        :rtype: odoo.http.Response
        """
        event_data = request.get_json_data()
        _logger.info("Webhook notification received from Gelato:\n%s", pprint.pformat(event_data))

        if event_data['event'] == 'order_status_updated':
            # Check the signature of the webhook notification.
            order_id = int(event_data['orderReferenceId'])
            order_sudo = request.env['sale.order'].sudo().browse(order_id).exists()
            received_signature = request.httprequest.headers.get('signature', '')
            self._verify_notification_signature(received_signature, order_sudo)

            # Process the event.
            fulfillment_status = event_data.get('fulfillmentStatus')
            if fulfillment_status == 'failed':
                # Log a message on the order.
                log_message = _(
                    "Gelato could not proceed with the fulfillment of order %(order_reference)s:"
                    " %(gelato_message)s",
                    order_reference=order_sudo.display_name,
                    gelato_message=event_data['comment'],
                )
                order_sudo.message_post(
                    body=log_message, author_id=request.env.ref('base.partner_root').id
                )
            elif fulfillment_status == 'canceled':
                # Cancel the order.
                order_sudo.with_user(SUPERUSER_ID)._action_cancel()

                # Manually cache the currency while in a sudoed environment to prevent an
                # AccessError. The state of the sales order is a dependency of
                # `untaxed_amount_to_invoice`, which is a monetary field. They require the currency
                # to ensure the values are saved in the correct format. However, the currency cannot
                # be read directly during the flush due to access rights, necessitating manual
                # caching.
                order_sudo.order_line.currency_id

                # Log a message on the order.
                log_message = _(
                    "Gelato has canceled order %(reference)s.", reference=order_sudo.display_name
                )
                order_sudo.message_post(
                    body=log_message, author_id=request.env.ref('base.partner_root').id
                )
            elif fulfillment_status == 'in_transit':
                # Send the Gelato order status update email.
                tracking_data = self._extract_tracking_data(item_data=event_data['items'])
                order_sudo.with_context({'tracking_data': tracking_data}).message_post_with_source(
                    source_ref=request.env.ref('sale_gelato.order_status_update'),
                    subtype_xmlid='mail.mt_comment',
                    author_id=request.env.ref('base.partner_root').id,
                )
            elif fulfillment_status == 'delivered':
                # Send the Gelato order status update email.
                order_sudo.with_context({'order_delivered': True}).message_post_with_source(
                    source_ref=request.env.ref('sale_gelato.order_status_update'),
                    subtype_xmlid='mail.mt_comment',
                    author_id=request.env.ref('base.partner_root').id,
                )
            elif fulfillment_status == 'returned':
                # Log a message on the order.
                log_message = _(
                    "Gelato has returned order %(reference)s.", reference=order_sudo.display_name
                )
                order_sudo.message_post(
                    body=log_message, author_id=request.env.ref('base.partner_root').id
                )
        return request.make_json_response('')

    @staticmethod
    def _verify_notification_signature(received_signature, order_sudo):
        """ Check if the received signature matches the expected one.

        :param str received_signature: The received signature.
        :param sale.order order_sudo: The sales order for which the webhook notification was sent.
        :return: None
        :raise Forbidden: If the signatures don't match.
        """
        company_sudo = order_sudo.company_id.sudo()  # In sudo mode to read on the company.
        expected_signature = company_sudo.gelato_webhook_secret
        if not expected_signature:
            _logger.warning(
                "gelato_webhook_secret not set for this company %s (id: %s)",
                company_sudo.name, company_sudo.id
            )
            raise Forbidden()

        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()

    @staticmethod
    def _extract_tracking_data(item_data):
        """ Extract the tracking URL and code from the item data.

        :param dict item_data: The item data.
        :return: The extracted tracking data.
        :rtype: dict
        """
        tracking_data = {}
        for i in item_data:
            for fulfilment_data in i['fulfillments']:
                tracking_data.setdefault(
                    fulfilment_data['trackingUrl'], fulfilment_data['trackingCode']
                )  # Different items can have the same tracking URL.
        return tracking_data
