# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from markupsafe import Markup
from werkzeug.exceptions import Forbidden

from odoo import SUPERUSER_ID, _, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GelatoController(http.Controller):
    _webhook_url = '/gelato/webhook'

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def gelato_webhook(self):
        """ Process the notification data sent by Gelato to the webhook.
        """
        event = request.get_json_data()
        _logger.info('Notification received from Gelato with data:\n%s', pprint.pformat(event))
        gelato_webhook_signature = request.httprequest.headers.get('signature', '')
        sale_order_id = int(event.get('orderReferenceId'))
        self.verify_gelato_notification(gelato_webhook_signature, sale_order_id)

        sale_order_sudo = request.env['sale.order'].sudo().browse(sale_order_id).exists()
        if event['event'] == 'order_status_updated':
            if event.get('fulfillmentStatus') == 'canceled':
                template = request.env.ref('sale.mail_template_sale_cancellation')

                sale_order_sudo.with_user(SUPERUSER_ID)._action_cancel()
                # The currency is manually cached while in a sudoed environment to prevent an
                # AccessError. The state of the Sales Order is a dependency of
                # `untaxed_amount_to_invoice`, which is a monetary field. They require the
                # currency to ensure the values are saved in the correct format. However, the
                # currency cannot be read directly during the flush due to access rights,
                # necessitating manual caching.
                sale_order_sudo.order_line.currency_id
                sale_order_sudo.message_post_with_source(
                    source_ref=template,
                    author_id=request.env.ref('base.partner_root').id,
                )

            elif event.get('fulfillmentStatus') == 'failed':
                sale_order_sudo.message_post(
                    body=event['comment'],
                    author_id=request.env.ref('base.partner_root').id,
                )

            elif event.get('fulfillmentStatus') == 'shipped':
                tracking_codes = self.get_tracking_codes(items=event['items'])
                message = Markup("{}<br/>").format(_("Your order has been passed to a carrier."))
                sale_order_sudo.message_post(
                    body=self.tracking_code_message(message, tracking_codes),
                    message_type='email',
                    author_id=request.env.ref('base.partner_root').id,
                    partner_ids=sale_order_sudo.partner_id.ids
                )

            elif event.get('fulfillmentStatus') == 'in_transit':
                message = Markup("{}<br/>").format(_("Carrier is handling the order delivery."))
                tracking_codes = self.get_tracking_codes(items=event['items'])

                sale_order_sudo.message_post(
                    body=self.tracking_code_message(message, tracking_codes),
                    message_type='email',
                    author_id=request.env.ref('base.partner_root').id,
                    partner_ids=sale_order_sudo.partner_id.ids
                )
            elif event.get('fulfillmentStatus') == 'delivered':
                sale_order_sudo.message_post(
                    body=_("Your package(s) has been delivered by carrier."),
                    message_type='email',
                    author_id=request.env.ref('base.partner_root').id,
                    partner_ids=sale_order_sudo.partner_id.ids
                )

    @staticmethod
    def verify_gelato_notification(webhook_secret, sale_order_id):
        """ Check that the received signature matches the expected one.

        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the
                signatures don't match
        """
        sale_order = request.env['sale.order'].sudo().search([('id', "=", sale_order_id)], limit=1)
        if webhook_secret != sale_order.company_id.gelato_webhook_secret:
            _logger.warning('received notification with invalid signature')
            raise Forbidden()

    @staticmethod
    def get_tracking_codes(items):
        """ Check that the received signature matches the expected one.

        :return: List of dicts containing tracking url and tracking code.
        """
        tracking_codes = []
        for i in items:
            for fulfilment in i['fulfillments']:
                if fulfilment['trackingUrl'] not in (val.get('tracking_url') for val in
                                                     tracking_codes):
                    tracking_codes.append({
                        'tracking_url': fulfilment['trackingUrl'],
                        'tracking_code': fulfilment['trackingCode']
                    })
        return tracking_codes

    @staticmethod
    def tracking_code_message(message, tracking_codes):
        message += "Track your package(s) here:"
        for elem in tracking_codes:
            message += Markup('</br> <a href=%s>%s</a> </br> ') % (
                elem['tracking_url'],
                elem['tracking_code']
            )
        return message
