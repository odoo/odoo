# -*- coding: utf-8 -*-

import json
import logging
import requests
import werkzeug
import pprint


from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class MollieController(http.Controller):
    _notify_url = '/payment/mollie/notify/'
    _redirect_url = '/payment/mollie/redirect/'
    _cancel_url = '/payment/mollie/cancel/'

    @http.route([
        '/payment/mollie/notify'],
        type='http', auth='none', methods=['GET'])
    def mollie_notify(self, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        request.env['payment.transaction'].sudo().form_feedback(post, 'mollie')
        return werkzeug.utils.redirect("/shop/payment/validate")

    @http.route([
        '/payment/mollie/redirect'], type='http', auth="none", methods=['GET'])
    def mollie_redirect(self, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        request.env['payment.transaction'].sudo().form_feedback(post, 'mollie')
        return werkzeug.utils.redirect("/shop/payment/validate")

    @http.route([
        '/payment/mollie/cancel'], type='http', auth="none", methods=['GET'])
    def mollie_cancel(self, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        request.env['payment.transaction'].sudo().form_feedback(post, 'mollie')
        return werkzeug.utils.redirect("/shop/payment/validate")

    @http.route([
        '/payment/mollie/intermediate'], type='http', auth="none", methods=['POST'], csrf=False)
    def mollie_intermediate(self, **post):
        acquirer = request.env['payment.acquirer'].browse(int(post['Key']))

        url = post['URL'] + "payments"
        headers = {'content-type': 'application/json', 'Authorization': 'Bearer ' + acquirer._get_mollie_api_keys(acquirer.environment)['mollie_api_key'] }
        base_url = post['BaseUrl']
        orderid = post['OrderId']
        description = post['Description']
        currency = post['Currency']
        amount = post['Amount']
        language = post['Language']
        name = post['Name']
        email = post['Email']
        zip = post['Zip']
        address = post['Address']
        town = post['Town']
        country = post['Country']
        phone = post['Phone']

        payload = {
            "description": description,
            "amount": amount,
            #"webhookUrl": base_url + self._notify_url,
            "redirectUrl": "%s%s?reference=%s" % (base_url, self._redirect_url, orderid),
            "metadata": {
                "order_id": orderid,
                "customer": {
                    "locale": language,
                    "currency": currency,
                    "last_name": name,
                    "address1": address,
                    "zip_code": zip,
                    "city": town,
                    "country": country,
                    "phone": phone,
                    "email": email
                }
            }
        }

        mollie_response = requests.post(
            url, data=json.dumps(payload), headers=headers).json()

        if mollie_response["status"] == "open":

            payment_tx = request.env['payment.transaction'].sudo().search([('reference', '=', orderid)])
            if not payment_tx or len(payment_tx) > 1:
                error_msg = ('received data for reference %s') % (pprint.pformat(orderid))
                if not payment_tx:
                    error_msg += ('; no order found')
                else:
                    error_msg += ('; multiple order found')
                _logger.info(error_msg)
                raise ValidationError(error_msg)
            payment_tx.write({"acquirer_reference": mollie_response["id"]})

            payment_url = mollie_response["links"]["paymentUrl"]
            return werkzeug.utils.redirect(payment_url)

        return werkzeug.utils.redirect("/")
