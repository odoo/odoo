# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo import http
from werkzeug import urls
from werkzeug.exceptions import Forbidden
_logger = logging.getLogger(__name__)


class XenditController(http.Controller):

    _webhook_url = '/payment/xendit/notification'
    _return_url = '/payment/status'

    @http.route('/payment/xendit/payment_methods', type='json', auth='public')
    def xendit_create_invoice(self, provider_id, amount, reference, currency_id, partner_id=None, **kwargs):
        """ Create an invoice on xendit which will return a invoice_url
        POST https://api.xendit.co/v2/invoices

        params:
        external_id (str) - name of where the sale is generated from
        amount (int) - amount to be paid in xendit checkout page
        description (str) - description if any
        success_redirect_url (str) - url to redirect to after payment is successful
        failure_redirect_url (str)- url to redirect to after payment fails
        """

        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id)
        base_url = provider_sudo.get_base_url()
        currency_code = request.env['res.currency'].browse(currency_id).name
        partner_sudo = partner_id and request.env['res.partner'].sudo().browse(partner_id).exists()
        payload = {
            "external_id": reference,
            "amount": amount,
            "currency": currency_code,
            "description": reference,
            "customer": {
                "given_names": partner_sudo.name,
            },
            "success_redirect_url": urls.url_join(base_url, self._return_url),
            "failure_redirect_url": urls.url_join(base_url, self._return_url),
        }

        if partner_sudo.phone_sanitized:
            payload['customer']['mobile_number'] = partner_sudo.phone_sanitized
        if partner_sudo.email:
            payload['customer']['email'] = partner_sudo.email

        checkout_url = provider_sudo._xendit_make_request('INVOICE', payload=payload).get('invoice_url')
        if not checkout_url:
            raise ValidationError("Issue on invoice creation on Xendit! No checkout URL received!")
        _logger.info("Xendit: redirecting to %s", checkout_url)

        return {
            "type": "ir.actions.act_url",
            "url": checkout_url,
            "target": "new",
        }

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def xendit_webhook(self):
        """ Process notification sent by customer. The 2 possible webhooks right now are invoices paid AND refund success/failure"""
        data = request.get_json_data()
        _logger.info("Received callback from Xendit: %s", pprint.pformat(data))

        try:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'xendit', data
            )
            if data.get('event') in ("refund.succeeded", "refund.failed"):
                data = data.get('data')

            received_signature = request.httprequest.headers.get('x-callback-token')
            self._xendit_verify_notification_signature(received_signature, tx_sudo)

            tx_sudo._handle_notification_data('xendit', data)
        except ValidationError:
            _logger.exception("Unable to handle notification data; skip to acknowledge")

        return request.make_json_response('')

    @staticmethod
    def _xendit_verify_notification_signature(received_signature, tx_sudo):
        """Checking received signature if matching the configured field on payment provider

        Making sure that the notification data is coming from xendit
        """
        if not received_signature:
            _logger.warning("No signature received on the callback!")
            raise Forbidden()

        xendit_token = tx_sudo.provider_id.xendit_webhook_token
        if xendit_token != received_signature:
            _logger.warning("Received signature is not matching the configured token! Transaction ignored!")
            raise Forbidden()
