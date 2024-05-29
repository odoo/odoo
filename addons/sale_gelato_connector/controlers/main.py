
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint
import logging
import requests
import json
from odoo.http import request
from odoo import http, _, SUPERUSER_ID
from odoo.addons.sale_gelato_connector.const import HANDLED_GELATO_EVENTS
from werkzeug.exceptions import Forbidden


_logger = logging.getLogger(__name__)


class GelatoController(http.Controller):
    _webhook_url = '/gelato/webhook'

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def gelato_webhook(self):
        event = request.get_json_data()
        _logger.info("Notification received from Gelato with data:\n%s", pprint.pformat(event))
        gelato_webhook_signature = request.httprequest.headers.get('signature','')
        self.verify_gelato_notification(gelato_webhook_signature)

        if event['event'] in HANDLED_GELATO_EVENTS:
            sale_order_id = event.get('orderReferenceId') #maybe throw an error if no sale_order_id
            sale_order = request.env['sale.order'].sudo().search([('id', '=', sale_order_id)], limit=1)
            if event['event'] == 'order_status_updated':
                if event.get('fulfillmentStatus') == 'canceled':
                    sale_order.message_post(
                        email_from=sale_order.user_id.email_formatted,
                        body=self.construck_message(sale_order),
                        message_type='comment',
                        email_layout_xmlid='mail.mail_notification_light',
                        partner_ids=[sale_order.partner_id.id,],
                    )

                elif event.get('fulfillmentStatus') == 'failed': #note: if items have different fullfilmnet centers, two notifications will be send
                    # should we send infi about failure to client or should it be only for backend user?
                    sale_order.message_post(
                        body=event['comment'],
                    )

                elif event.get('fulfillmentStatus') == 'shipped': #note: if items have different fullfilmnet centers, two notifications will be send
                    sale_order.message_post(
                        body=_("The order has been passed to carrier."),
                    )
                elif event.get('fulfillmentStatus') == 'in_transit': #note: if items have different fullfilmnet centers, two notifications will be send
                    sale_order.message_post(
                        body=_("Carrier is handling the order delivery."),
                    )
                elif event.get('fulfillmentStatus') == 'delivered': #note: if items have different fullfilmnet centers, two notifications will be send
                    sale_order.message_post(
                        body=_("The order has been delivered by carrier."),
                    )

    @staticmethod
    def construck_message(sale_order):
        body = _('Dear %s, \n Please be advised that your Sales Order %s has been cancelled. Therefore, you should not be charged further for this order. If any refund is necessary, this will be executed at best convenience. Do not hesitate to contact us if you have any questions.',sale_order.partner_id.name, sale_order.name)
        return body

    @staticmethod
    def verify_gelato_notification(webhook_secret):
        if not webhook_secret == 'fkNiXwzGcPE8IYJsfIGkTYXZ2hhCJSEdNJAbfQXfYHM1A6dlTy':
            _logger.warning("received notification with invalid signature")
            raise Forbidden()