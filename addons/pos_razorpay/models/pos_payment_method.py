from hashlib import sha1

from odoo.exceptions import UserError
from odoo import fields, models, api, _
from odoo.tools import consteq, hmac

from .razorpay_pos_request import RazorpayPosRequest


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    razorpay_tid = fields.Char(string='Razorpay Device Serial No', help='Device Serial No \n ex: 7000012300')
    razorpay_allowed_payment_modes = fields.Selection(selection=[('all', 'All'), ('card', 'Card'), ('upi', 'UPI'), ('bharatqr', 'BHARATQR')], default='all', help='Choose allow payment mode: \n All/Card/UPI or QR')
    razorpay_username = fields.Char(string='Razorpay Username', help='Username(Device Login) \n ex: 1234500121')
    razorpay_api_key = fields.Char(string='Razorpay API Key', help='Used when connecting to Razorpay: https://razorpay.com/docs/payments/dashboard/account-settings/api-keys/', groups='point_of_sale.group_pos_manager')
    razorpay_test_mode = fields.Boolean(string='Razorpay Test Mode', default=False, help='Turn it on when in Test Mode')

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('razorpay', 'Razorpay')]

    def razorpay_make_refund_request(self, data):
        razorpay = RazorpayPosRequest(self)
        request_body = razorpay._razorpay_get_request_parameters()
        if data.get('refund_type') == 'refund':
            request_body.update({
                'amount': data.get('amount'),
                'originalTransactionId': data.get('transaction_id'),
                'externalRefNumber': data.get('externalRefNumber')
            })
        else:
            request_body.update({
                'txnId': data.get('transaction_id'),
            })
        endpoint = 'unified/refund' if data.get('refund_type') == 'refund' else 'void'
        response = razorpay._call_razorpay(endpoint=endpoint, payload=request_body)
        if response.get('success') and not response.get('errorCode'):
            return {
                'status': response.get('status'),
                'authCode': response.get('authCode'),
                'cardLastFourDigit': response.get('cardLastFourDigit'),
                'externalRefNumber': response.get('externalRefNumber'),
                'reverseReferenceNumber': response.get('reverseReferenceNumber'),
                'txnId': response.get('txnId'),
                'paymentMode': response.get('paymentMode'),
                'paymentCardType': response.get('paymentCardType'),
                'paymentCardBrand': response.get('paymentCardBrand'),
                'nameOnCard': response.get('nameOnCard'),
                'acquirerCode': response.get('acquirerCode'),
                'postingDate': response.get('postingDate'),
            }
        default_error_msg = _('The Razorpay POS refund request has encountered an unexpected error code.')
        error = response.get('errorMessage') or default_error_msg
        return {'error': str(error)}

    def razorpay_make_payment_request(self, data):
        razorpay = RazorpayPosRequest(self)
        body = razorpay._razorpay_get_payment_request_body(payment_mode=True)
        body.update({
            'amount': data.get('amount'),
            'externalRefNumber': data.get('referenceId')
        })
        response = razorpay._call_razorpay(endpoint='pay', payload=body)
        if response.get('success') and not response.get('errorCode'):
            p2p_request_id = str(response.get('p2pRequestId'))
            return {
                'success': True,
                'p2pRequestId': p2p_request_id,
                'signature': self._razorpay_sign_transaction(p2p_request_id, data['referenceId'], data['amount']),
            }
        default_error_msg = _('Razorpay POS payment request expected errorCode not found in the response')
        error = response.get('errorMessage') or default_error_msg
        return {'error': str(error)}

    def razorpay_fetch_payment_status(self, data):
        razorpay = RazorpayPosRequest(self)
        body = razorpay._razorpay_get_request_parameters()
        body.update({'origP2pRequestId': data.get('p2pRequestId')})
        response = razorpay._call_razorpay(endpoint='status', payload=body)
        if response.get('success') and not response.get('errorCode'):
            payment_status = response.get('status')
            payment_messageCode = response.get('messageCode')
            if payment_status == 'AUTHORIZED' and payment_messageCode == 'P2P_DEVICE_TXN_DONE':
                return {
                    'status': response.get('status'),
                    'authCode': response.get('authCode'),
                    'cardLastFourDigit': response.get('cardLastFourDigit'),
                    'externalRefNumber': response.get('externalRefNumber'),
                    'reverseReferenceNumber': response.get('reverseReferenceNumber'),
                    'txnId': response.get('txnId'),
                    'paymentMode': response.get('paymentMode'),
                    'paymentCardType': response.get('paymentCardType'),
                    'paymentCardBrand': response.get('paymentCardBrand'),
                    'nameOnCard': response.get('nameOnCard'),
                    'acquirerCode': response.get('acquirerCode'),
                    'createdTime': response.get('createdTime'),
                    'p2pRequestId': response.get('p2pRequestId'),
                    'settlementStatus': response.get('settlementStatus'),
                }
            elif payment_status in ['VOIDED', 'AUTHORIZED_REFUNDED'] and payment_messageCode == 'P2P_DEVICE_TXN_DONE':
                return {
                    'status': payment_status,
                    'settlementStatus': response.get('settlementStatus'),
                }
            elif payment_status == 'FAILED' or payment_messageCode == 'P2P_DEVICE_CANCELED':
                return {'error': str(response.get('message', _('Razorpay POS transaction failed'))),
                        'payment_messageCode': payment_messageCode}
            elif payment_messageCode in ['P2P_DEVICE_RECEIVED', 'P2P_DEVICE_SENT', 'P2P_STATUS_QUEUED']:
                return {'status': payment_messageCode.split('_')[-1]}
        default_error_msg = _('Razorpay POS payment status request expected errorCode not found in the response')
        error = response.get('errorMessage') or default_error_msg
        return {'error': str(error)}

    def razorpay_cancel_payment_request(self, data):
        razorpay = RazorpayPosRequest(self)
        body = razorpay._razorpay_get_payment_request_body(payment_mode=False)
        body.update({'origP2pRequestId': data.get('p2pRequestId')})
        response = razorpay._call_razorpay(endpoint='cancel', payload=body)
        if response.get('success') and not response.get('errorCode'):
            return {'error': _('Razorpay POS transaction canceled successfully')}
        default_error_msg = _('Razorpay POS payment cancel request expected errorCode not found in the response')
        errorMessage = response.get('errorMessage') or default_error_msg
        return {'errorMessage': str(errorMessage)}

    @api.constrains('payment_provider')
    def _check_razorpay_terminal(self):
        if any(record.payment_provider == 'razorpay' and record.company_id.currency_id.name != 'INR' for record in self):
            raise UserError(_('This Payment Terminal is only valid for INR Currency'))

    @api.model
    def _allowed_actions_in_self_order(self):
        return super()._allowed_actions_in_self_order() + ['razorpay_make_payment_request', 'razorpay_fetch_payment_status', 'razorpay_cancel_payment_request']

    def _razorpay_sign_transaction(self, p2p_request_id, reference_id, amount):
        # Razorpay status responses don't include the requested amount, so the
        # signature proves which reference and amount a p2p request was made for.
        return hmac(self.env(su=True), 'pos_razorpay', f'{p2p_request_id}/{reference_id}/{float(amount)}')

    def _is_valid_self_order_payment(self, pos_config, order, payment):
        if self.payment_provider != 'razorpay':
            return super()._is_valid_self_order_payment(pos_config, order, payment)
        p2p_request_id = str(payment.get('razorpay_p2p_request_id') or '')
        # Same reference as `_processRazorpay` builds for the only payment of a
        # kiosk order: `payment['amount']` is the JSON number sent by the
        # frontend, so `str()` formats it as the frontend does.
        reference_id = sha1(
            f"{pos_config.id}/{order['uuid']}/{self.id}/{pos_config.currency_id.name}/{payment['amount']}/1".encode()
        ).hexdigest()
        expected_signature = self._razorpay_sign_transaction(p2p_request_id, reference_id, payment['amount'])
        if not p2p_request_id or not consteq(str(payment.get('razorpay_signature') or ''), expected_signature):
            return False
        if self.env['pos.payment'].search_count([
            ('payment_method_id', '=', self.id),
            ('razorpay_p2p_request_id', '=', p2p_request_id),
        ], limit=1):
            return False
        status = self.razorpay_fetch_payment_status({'p2pRequestId': p2p_request_id})
        return status.get('status') == 'AUTHORIZED' and status.get('externalRefNumber') == reference_id
