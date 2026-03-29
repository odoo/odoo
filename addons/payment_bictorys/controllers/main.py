# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class BictorysController(http.Controller):
    _return_url = '/payment/bictorys/return'
    _webhook_url = '/payment/bictorys/webhook'
    _pos_webhook_url = '/payment/bictorys/pos/webhook'

    # === ONLINE PAYMENT: return URL === #

    @http.route('/payment/bictorys/return', type='http', methods=['GET'], auth='public', csrf=False)
    def bictorys_return_from_checkout(self, **data):
        _logger.info("Bictorys: return from checkout with data:\n%s", pprint.pformat(data))
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('reference', '=', data.get('ref')),
            ('provider_code', '=', 'bictorys'),
        ], limit=1)

        if not tx_sudo:
            _logger.warning("Bictorys: no transaction found for reference %s", data.get('ref'))
            return request.redirect('/payment/status?status=error')

        # Handle success or cancellation based on the return parameter.
        status = data.get('status')
        if status == 'success':
            tx_sudo._set_done()
        elif status == 'cancel':
            tx_sudo._set_canceled()
        else:
            # Fallback: attempt verification via the API.
            try:
                tx_sudo._handle_notification_data('bictorys', data)
            except ValidationError:
                _logger.warning(
                    "Bictorys: unable to verify transaction via API, skipping."
                )

        return request.redirect('/payment/status')

    # === ONLINE PAYMENT: webhook === #

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def bictorys_webhook(self):
        """ Process webhook notifications for online (eCommerce) payments. """
        data = request.get_json_data()
        _logger.info("Bictorys: online webhook received:\n%s", pprint.pformat(data))
        try:
            self._verify_notification_signature(data)
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'bictorys', data
            )
            tx_sudo._handle_notification_data('bictorys', data)
        except ValidationError:
            _logger.warning(
                "Bictorys: unable to handle notification data; skipping.", exc_info=True
            )
        return request.make_json_response('')

    # === POS PAYMENT: webhook === #

    @http.route(_pos_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def bictorys_pos_webhook(self):
        """ Process POS payment notifications sent by Bictorys.

        When a payment is confirmed or rejected on the Bictorys terminal:
        1. Store the notification on the pos.payment.method record.
        2. Push a WebSocket event to the POS session so the JS handler picks it up.

        This follows the same pattern as pos_adyen.
        """
        data = request.get_json_data() or {}
        _logger.info("Bictorys: POS webhook received:\n%s", pprint.pformat(data))

        # Retrieve the order reference sent by Bictorys.
        payment_reference = data.get('paymentReference')

        if payment_reference:
            order = request.env['pos.order'].sudo().search(
                [('pos_reference', '=', payment_reference)],
                limit=1,
            )
            if order:
                payment_status = data.get('status')
                if payment_status == 'succeeded':
                    order.write({'bictorys_payment_status': 'succeeded'})
                    _logger.info("Bictorys: order %s marked as succeeded", order.name)
                elif payment_status in ('failed', 'cancelled'):
                    order.write({'bictorys_payment_status': 'failed'})
                    _logger.info("Bictorys: order %s marked as failed", order.name)
            else:
                _logger.warning(
                    "Bictorys: no POS order found with pos_reference=%s", payment_reference
                )

        # Verify the webhook secret.
        bictorys_provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'bictorys'), ('state', '!=', 'disabled')], limit=1
        )
        if not bictorys_provider:
            _logger.warning("Bictorys POS webhook: no active provider found.")
            return request.make_json_response('')

        received_secret = request.httprequest.headers.get('X-Secret-Key', '')
        if received_secret != bictorys_provider.bictorys_webhook_secret:
            _logger.warning("Bictorys POS webhook: invalid webhook secret.")
            raise Forbidden()

        # Identify the POS payment method by terminal identifier.
        device_id = data.get('deviceId') or data.get('merchantId')
        bictorys_pm = (
            request.env['pos.payment.method'].sudo().search(
                [('bictorys_terminal_identifier', '=', device_id)], limit=1
            )
            if device_id
            else request.env['pos.payment.method'].sudo().search(
                [('use_payment_terminal', '=', 'bictorys')], limit=1
            )
        )

        if not bictorys_pm:
            _logger.warning(
                "Bictorys POS webhook: no pos.payment.method found for device '%s'.", device_id
            )
            return request.make_json_response('')

        bictorys_pm.bictorys_latest_response = json.dumps(data)

        # Notify the POS session via WebSocket (same pattern as pos_adyen).
        pos_session = request.env['pos.session'].sudo().search(
            [('config_id.payment_method_ids', 'in', bictorys_pm.ids), ('state', '=', 'opened')],
            limit=1,
        )
        if pos_session:
            pos_session.config_id._notify('BICTORYS_LATEST_RESPONSE', pos_session.config_id.id)
            _logger.info("Bictorys: notified POS session %s via WebSocket.", pos_session.id)

        return request.make_json_response('')

    # === HELPERS === #

    def _verify_notification_signature(self, notification_data):
        bictorys_provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'bictorys'), ('state', '!=', 'disabled')], limit=1
        )
        if not bictorys_provider:
            raise Forbidden()
        received_secret = request.httprequest.headers.get('X-Secret-Key', '')
        if received_secret != bictorys_provider.bictorys_webhook_secret:
            _logger.warning("Bictorys: invalid webhook secret in online notification.")
            raise Forbidden()