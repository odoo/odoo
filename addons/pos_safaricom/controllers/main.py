# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import http
from odoo.http import request
from odoo.tools import verify_hash_signed


class SafaricomController(http.Controller):

    @http.route('/pos_safaricom/callback', type='http', auth='public', methods=['POST'], csrf=True)
    def safaricom_callback(self, payload):
        """
        Handle M-Pesa STK Push callback
        """

        try:
            raw_data = request.httprequest.data.decode('utf-8') if request.httprequest.data else ''

            # Verify the signed payload to get the payment method ID
            decoded_payload = verify_hash_signed(request.env["pos.payment.method"].sudo().env, "pos_safaricom", payload)

            if raw_data and decoded_payload:
                stk_callback = json.loads(raw_data).get('Body', {}).get('stkCallback', {})

                if stk_callback:
                    result_code = stk_callback.get('ResultCode')
                    result_desc = stk_callback.get('ResultDesc')
                    checkout_request_id = stk_callback.get('CheckoutRequestID')
                    merchant_request_id = stk_callback.get('MerchantRequestID')
                    callback_metadata = stk_callback.get('CallbackMetadata', {})

                    # Find the specific payment method using the signed payload
                    payment_method = request.env['pos.payment.method'].sudo().search([
                        ('id', '=', decoded_payload.get('payment_method_id')),
                    ], limit=1)

                    if payment_method:
                        payment_method.retrieve_payment_status(
                            merchant_request_id,
                            checkout_request_id,
                            result_code,
                            result_desc,
                            callback_metadata,
                        )

            return request.make_response(json.dumps({
                "ResultCode": "0",
                "ResultDesc": "Accepted",
            }), [('Content-Type', 'application/json')])

        except (json.JSONDecodeError, ValueError):
            return request.make_response(json.dumps({
                "ResultCode": "1",
                "ResultDesc": "Error processing callback",
            }), [('Content-Type', 'application/json')])

    @http.route('/c2b/validation/callback', type="http", auth='public', methods=['POST'], csrf=True)
    def c2b_validation_callback(self, payload):
        """
        Validate the payment before charging the customer
        For now, we accept all payments (ResponseType is set to 'Completed')
        """
        try:
            raw_data = request.httprequest.data.decode('utf-8') if request.httprequest.data else ''
            decoded_payload = verify_hash_signed(request.env["pos.payment.method"].sudo().env, "pos_safaricom", payload)

            if raw_data and decoded_payload:

                return request.make_response(json.dumps({
                    "ResultCode": "0",
                    "ResultDesc": "Accepted",
                }), [('Content-Type', 'application/json')])

        except (json.JSONDecodeError, ValueError):
            return request.make_response(json.dumps({
                        "ResultCode": "C2B00011",
                        "ResultDesc": "Rejected",
                    }), [('Content-Type', 'application/json')])

    @http.route('/c2b/confirmation/callback', type='http', auth='public', methods=['POST'], csrf=True)
    def c2b_confirmation_callback(self, payload):
        """
        Handle C2B payment confirmation via Lipa na M-PESA
        """
        try:
            raw_data = request.httprequest.data.decode('utf-8') if request.httprequest.data else ''
            decoded_payload = verify_hash_signed(request.env["pos.payment.method"].sudo().env, "pos_safaricom", payload)

            if raw_data and decoded_payload:
                data = json.loads(raw_data)

                trans_id = data.get('TransID')
                trans_amount = data.get('TransAmount')
                msisdn = data.get('MSISDN')
                name = data.get('FirstName')

                payment_method = request.env['pos.payment.method'].sudo().search([
                        ('id', '=', decoded_payload.get('payment_method_id')),
                    ], limit=1)

                if payment_method:
                    payment_method.create_payment_transaction(trans_id, trans_amount, msisdn, name)

                return request.make_response(json.dumps({
                    "ResultCode": "0",
                    "ResultDesc": "Accepted",
                }), [('Content-Type', 'application/json')])

        except (json.JSONDecodeError, ValueError):
            return request.make_response(json.dumps({
                "ResultCode": "C2B00011",
                "ResultDesc": "Rejected",
            }), [('Content-Type', 'application/json')])
