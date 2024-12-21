from odoo import api, fields, models,  _
from odoo.exceptions import UserError

from .pinelabs_pos_request import PinelabsPosRequest
MAX_RETRIES = 30
PINELABS_ERROR_CODES_MAPPING = {
    "CANNOT CANCEL AS TRANSACTION IS IN PROGRESS": [11, "The transaction is still being processed and cannot be canceled at this time"],
    "TRANSACTION NOT FOUND": [12, "No transaction was found with the provided reference ID"],
    "INVALID PLUTUS TXN REF ID": [13, "The Plutus reference ID provided is invalid."]
}


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    pinelabs_merchant = fields.Char(string='Pine Labs Merchant ID', help='A merchant id issued directly to the merchant by Pine Labs.', copy=False)
    pinelabs_store = fields.Char(string='Pine Labs Store ID', help='A store id issued directly to the merchant by Pine Labs.', copy=False)
    pinelabs_client = fields.Char(string='Pine Labs Client ID', help='A client id issued directly to the merchant by Pine Labs.', copy=False)
    pinelabs_security_token = fields.Char(string='Pine Labs Security Token', help='A security token issued directly to the merchant by Pine Labs.')
    pinelabs_allowed_payment_modes = fields.Selection(
        selection=[('all', "All"), ('card', "Card"), ('upi', "Upi")],
        string='Pine Labs Allowed Payment Modes',
        help='Accepted payment modes by Pine Labs for transactions.', copy=False)
    pinelabs_test_mode = fields.Boolean(string='Pine Labs Test Mode', help='test pinelabs transaction process.', copy=False)

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('pinelabs', 'Pine Labs')]

    def _is_write_forbidden(self, fields):
        # Allow the modification of pinelabs_latest_response field even if a pos_session is open
        return super(PosPaymentMethod, self)._is_write_forbidden(fields -  {'pinelabs_latest_response'})

    def pinelabs_make_payment_request(self, data):
        pinelabs = PinelabsPosRequest(self)
        body = pinelabs.pinelabs_request_body(payment_mode=True)
        body.update({
            'Amount': data['amount'],
            'TransactionNumber': data['transactionNumber'],
            'SequenceNumber': data['sequenceNumber']
        })
        response = pinelabs.call_pinelabs(endpoint='UploadBilledTransaction', payload=body)
        if response.get('ResponseCode') == 0 and response.get('ResponseMessage') == "APPROVED":
            return {
                'responseCode': response['ResponseCode'],
                'status': response['ResponseMessage'],
                'plutusTransactionReferenceID': response['PlutusTransactionReferenceID'],
            }
        return {"error": self._get_pinelabs_error_code_message(response.get('ResponseCode'), response.get('ResponseMessage'))['errorMessage']}

    def pinelabs_fetch_payment_status(self, data):
        pinelabs = PinelabsPosRequest(self)
        body = pinelabs.pinelabs_request_body(payment_mode=False)
        body.update({'PlutusTransactionReferenceID': data['plutusTransactionReferenceID']})
        response = pinelabs.call_pinelabs(endpoint='GetCloudBasedTxnStatus', payload=body)
        if response.get('ResponseCode') in [0, 1001]:
            return {
                'responseCode': response['ResponseCode'],
                'status': response['ResponseMessage'],
                'plutusTransactionReferenceID': response['PlutusTransactionReferenceID'],
                'data': format_transaction_data(response['TransactionData']) if response['ResponseCode'] == 0 else {},
            }
        return {'error': self._get_pinelabs_error_code_message(response.get('ResponseCode'), response.get('ResponseMessage'))['errorMessage']}

    def pinelabs_cancel_payment_request(self, data):
        pinelabs = PinelabsPosRequest(self)
        body = pinelabs.pinelabs_request_body(payment_mode=False)
        body.update({
            'Amount': data['amount'],
            'PlutusTransactionReferenceID': data['plutusTransactionReferenceID'],
        })
        response = pinelabs.call_pinelabs(endpoint='CancelTransaction', payload=body)
        if response.get('ResponseCode') == 0 and response.get('ResponseMessage') == "APPROVED":
            return {
                'responseCode': response['ResponseCode'],
                'error': _('Pine Labs POS transaction cancelled successfully')
            }
        return {
            'responseCode': self._get_pinelabs_error_code_message(response.get('ResponseCode'), response.get('ResponseMessage'))['responseCode'],
            'errorMessage': self._get_pinelabs_error_code_message(response.get('ResponseCode'), response.get('ResponseMessage'))['errorMessage']
        }

    @api.constrains('use_payment_terminal')
    def _check_pinelabs_terminal(self):
        if any(record.use_payment_terminal == 'pinelabs' and record.company_id.currency_id.name != 'INR' for record in self):
            raise UserError(_('This Payment Terminal is only valid for INR Currency'))

    def _get_pinelabs_error_code_message(self, response_code, response_message):
        error_mapping = PINELABS_ERROR_CODES_MAPPING.get(response_message)
        default_error_msg = _('The expected error code for the Pine Labs POS payment request was not included in the response.')
        if error_mapping:
            return {
                'responseCode': error_mapping[0],
                'errorMessage': error_mapping[1]
            }
        else:
            return {
                'responseCode': response_code,
                'errorMessage': response_message or default_error_msg
            }


def format_transaction_data(transaction_data):
    return { d['Tag']: d['Value'] for d in transaction_data }
