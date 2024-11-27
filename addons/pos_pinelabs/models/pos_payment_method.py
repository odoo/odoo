from odoo import api, fields, models,  _
from odoo.exceptions import UserError

from .pinelabs_pos_request import PinelabsPosRequest


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    pinelabs_merchant = fields.Char(string='Pine Labs Merchant ID', help='A merchant id issued directly to the merchant by Pine Labs.')
    pinelabs_store = fields.Char(string='Pine Labs Store ID', help='A store id issued directly to the merchant by Pine Labs.')
    pinelabs_client = fields.Char(string='Pine Labs Client ID', help='A client id issued directly to the merchant by Pine Labs.')
    pinelabs_security_token = fields.Char(string='Pine Labs Security Token', help='A security token issued directly to the merchant by Pine Labs.')
    pinelabs_allowed_payment_modes = fields.Selection(selection=[('all', "All"), ('card', "Card"), ('upi', "Upi")], string='Pine Labs Allowed Payment Modes', help='Accepted payment modes by Pine Labs for transactions.')

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('pinelabs', 'Pine Labs')]

    def pinelabs_make_payment_request(self, data):
        pinelabs = PinelabsPosRequest(self)
        body = pinelabs._pinelabs_request_body()
        body.update({
            'Amount': data.get('amount'),
            'TransactionNumber': data.get('transactionNumber'),
            'SequenceNumber': data.get('sequenceNumber')
        })
        response = pinelabs._call_pinelabs(endpoint='UploadBilledTransaction', payload=body)
        if not response.get('ResponseCode') and response.get('ResponseMessage') == "APPROVED":
            return {
                'responseCode': response.get('ResponseCode'),
                'status': response.get('ResponseMessage'),
                'plutusTransactionReferenceID': response.get('PlutusTransactionReferenceID'),
            }
        default_error_msg = _('The expected error code for the Pine Labs POS payment upload request was not included in the response.')
        error = response.get('ResponseMessage') or default_error_msg
        return {'error': str(error)}

    def pinelabs_fetch_payment_status(self, data):
        pinelabs = PinelabsPosRequest(self)
        body = pinelabs._pinelabs_request_body(payment_mode=False)
        body.update({'PlutusTransactionReferenceID': data.get('plutusTransactionReferenceID')})
        response = pinelabs._call_pinelabs(endpoint='GetCloudBasedTxnStatus', payload=body)
        if response.get('ResponseCode') in [0, 1001]:
            return {
                'responseCode': response.get('ResponseCode'),
                'status': response.get('ResponseMessage'),
                'plutusTransactionReferenceID': response.get('PlutusTransactionReferenceID'),
                'data': format_transaction_data(response.get('TransactionData')) if response.get('ResponseCode') == 0 else {},
            }
        default_error_msg = _('The expected error code for the Pine Labs POS payment status request was not included in the response.')
        error = response.get('ResponseMessage') or default_error_msg
        return {'error': str(error)}

    def pinelabs_cancel_payment_request(self, data):
        pinelabs = PinelabsPosRequest(self)
        body = pinelabs._pinelabs_request_body(payment_mode=False)
        body.update({
            'Amount': data.get('amount'),
            'PlutusTransactionReferenceID': data.get('plutusTransactionReferenceID'),
        })
        response = pinelabs._call_pinelabs(endpoint='CancelTransaction', payload=body)
        if not response.get('ResponseCode') and response.get('ResponseMessage') == "APPROVED":
            return {
                'responseCode': response.get('ResponseCode'),
                'error': _('Pine Labs POS transaction cancelled successfully')
            }
        default_error_msg = _('The expected error code for the Pine Labs POS payment cancellation request was not included in the response.')
        errorMessage = response.get('ResponseMessage') or default_error_msg
        return {
            'responseCode': response.get('ResponseCode'),
            'errorMessage': str(errorMessage)
        }

    @api.constrains('use_payment_terminal')
    def _check_pinelabs_terminal(self):
        if any(record.use_payment_terminal == 'pinelabs' and record.company_id.currency_id.name != 'INR' for record in self):
            raise UserError(_('This Payment Terminal is only valid for INR Currency'))


def format_transaction_data(transaction_data):
    return { d['Tag']: d['Value'] for d in transaction_data }
