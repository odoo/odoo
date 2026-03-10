# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request
from odoo.tools import verify_hash_signed


class SafaricomController(http.Controller):

    @http.route('/pos_safaricom/callback', type='http', auth='public', methods=['POST'])
    def safaricom_callback(self, payload):
        """
        Handle M-Pesa STK Push callback
        """

        try:
            data = request.get_json_data()

            # Verify the signed payload to get the payment method ID
            decoded_payload = verify_hash_signed(request.env["pos.payment.method"].sudo().env, "pos_safaricom", payload)

            # Find the specific payment method using the signed payload
            payment_method = request.env['pos.payment.method'].sudo().search([
                ('id', '=', decoded_payload.get('payment_method_id')),
            ], limit=1)

            if payment_method:
                payment_method._notify_stk_callback(data.get('Body', {}).get('stkCallback', {}))
                return request.make_json_response({"ResultCode": "0", "ResultDesc": "Accepted"})

            return request.make_json_response({"ResultCode": "1", "ResultDesc": "Error processing callback"})

        except ValueError:
            return request.make_json_response({"ResultCode": "1", "ResultDesc": "Error processing callback"})

    @http.route('/c2b/validation/callback', type="http", auth='public', methods=['POST'])
    def c2b_validation_callback(self, payload):
        """
        Validate the payment before charging the customer
        For now, we accept all payments (ResponseType is set to 'Completed')
        """
        try:
            data = request.get_json_data()
            decoded_payload = verify_hash_signed(request.env["pos.payment.method"].sudo().env, "pos_safaricom", payload)

            if data and decoded_payload:
                return request.make_json_response({"ResultCode": "0", "ResultDesc": "Accepted"})

        except ValueError:
            return request.make_json_response({"ResultCode": "C2B00011", "ResultDesc": "Rejected"})

    @http.route('/c2b/confirmation/callback', type='http', auth='public', methods=['POST'])
    def c2b_confirmation_callback(self, payload):
        """
        Handle C2B payment confirmation via Lipa na M-PESA
        """
        try:
            data = request.get_json_data()
            decoded_payload = verify_hash_signed(request.env["pos.payment.method"].sudo().env, "pos_safaricom", payload)

            if data and decoded_payload:
                trans_id = data.get('TransID')
                trans_amount = data.get('TransAmount')
                msisdn = data.get('MSISDN')
                name = data.get('FirstName')

                payment_method = request.env['pos.payment.method'].sudo().search([
                        ('id', '=', decoded_payload.get('payment_method_id')),
                    ], limit=1)

                if payment_method:
                    payment_method._create_payment_transaction(trans_id, trans_amount, msisdn, name)

                return request.make_json_response({"ResultCode": "0", "ResultDesc": "Accepted"})

        except ValueError:
            return request.make_json_response({"ResultCode": "C2B00011", "ResultDesc": "Rejected"})
