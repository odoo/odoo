# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from werkzeug.exceptions import Forbidden

from odoo import http, _, SUPERUSER_ID
from odoo.http import request

from odoo.addons.sale_gelato_connector.const import HANDLED_GELATO_EVENTS


_logger = logging.getLogger(__name__)


class GelatoController(http.Controller):
    _webhook_url = '/gelato/webhook'

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def gelato_webhook(self):
        event = request.get_json_data()
        _logger.info("Notification received from Gelato with data:\n%s", pprint.pformat(event))
        gelato_webhook_signature = request.httprequest.headers.get('signature', '')
        sale_order_id = event.get('orderReferenceId')
        self.verify_gelato_notification(gelato_webhook_signature, sale_order_id)

        if event['event'] in HANDLED_GELATO_EVENTS:
            sale_order = request.env['sale.order'].sudo().search(
                [('id', '=', sale_order_id)],
                        limit=1
                )
            if event['event'] == 'order_status_updated':
                if event.get('fulfillmentStatus') == 'canceled':

                    template = request.env.ref('sale.mail_template_sale_cancellation')
                    sale_order.message_post_with_source(
                        source_ref=template,
                    )
                    # sale_order.with_user(SUPERUSER_ID).sudo().with_context(
                    #     {'disable_cancel_warning': True}).action_cancel()

                elif event.get('fulfillmentStatus') == 'failed':
                    sale_order.message_post(body=event['comment'],).with_user(sale_order.user_id)

                elif event.get('fulfillmentStatus') == 'shipped':  # note: if items have different fullfilmnet centers, two notifications will be send
                    sale_order.message_post(body=_("The order has been passed to carrier."),)
                    for i in event['items']:
                        for y in i['fulfillments']:
                            sale_order.message_post(body=_("Track your package here: " + y['trackingUrl']))

                elif event.get('fulfillmentStatus') == 'in_transit':  # note: if items have different fullfilmnet centers, two notifications will be send
                    sale_order.message_post(
                        body=_("Carrier is handling the order delivery."),
                    )
                elif event.get('fulfillmentStatus') == 'delivered':  # note: if items have different fullfilmnet centers, two notifications will be send
                    sale_order.message_post(
                        body=_("The order has been delivered by carrier."),
                    )

    def verify_gelato_notification(self, webhook_secret, sale_order_id):

        sale_order = request.env['sale.order'].sudo().search([('id', "=", sale_order_id)], limit=1)
        if webhook_secret != sale_order.company_id.gelato_webhook_secret:

            _logger.warning("received notification with invalid signature")
            raise Forbidden()
