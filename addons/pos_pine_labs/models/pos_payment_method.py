from odoo import api, fields, models,  _
from odoo.exceptions import UserError

from .pine_labs_pos_request import call_pine_labs


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    pine_labs_merchant = fields.Char(string='Pine Labs Merchant ID', help='A merchant id issued directly to the merchant by Pine Labs.', copy=False)
    pine_labs_store = fields.Char(string='Pine Labs Store ID', help='A store id issued directly to the merchant by Pine Labs.', copy=False)
    pine_labs_client = fields.Char(string='Pine Labs Client ID', help='A client id issued directly to the merchant by Pine Labs.', copy=False)
    pine_labs_security_token = fields.Char(string='Pine Labs Security Token', help='A security token issued directly to the merchant by Pine Labs.')
    pine_labs_allowed_payment_mode = fields.Selection(
        selection=[('all', "All"), ('card', "Card"), ('upi', "Upi")],
        string='Pine Labs Allowed Payment Modes',
        help='Accepted payment modes by Pine Labs for transactions.')
    pine_labs_test_mode = fields.Boolean(string='Pine Labs Test Mode', help='Test Pine Labs transaction process.')

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('pine_labs', 'Pine Labs')]

    def pine_labs_make_payment_request(self, data):
        """
        Sends a payment request to the Pine Labs POS API.

        :param dict data: Contains `amount`, `transactionNumber`, and `sequenceNumber`.
        :return: On success, returns `responseCode`, `status`, and `plutusTransactionReferenceID`. 
                On failure, returns an error message.
        :rtype: dict
        """
        body = {
            'Amount': data['amount'],
            'TransactionNumber': data['transactionNumber'],
            'SequenceNumber': data['sequenceNumber']
        }
        response = call_pine_labs(payment_method=self, endpoint='UploadBilledTransaction', payload=body)
        if response.get('ResponseCode') == 0 and response.get('ResponseMessage') == "APPROVED":
            return {
                'responseCode': response['ResponseCode'],
                'status': response['ResponseMessage'],
                'plutusTransactionReferenceID': response['PlutusTransactionReferenceID'],
            }
        default_error = _('The expected error code for the Pine Labs POS status request was not included in the response.')
        error = response.get('ResponseMessage') or response.get('errorMessage') or default_error
        return {"error": error}

    def pine_labs_fetch_payment_status(self, data):
        """
        Fetches payment status from the Pine Labs POS API.

        :param dict data: Contains `plutusTransactionReferenceID` for the status request.
        :return: On success, returns `responseCode`, `status`, `plutusTransactionReferenceID`, and `data` (formatted transaction details). 
                On failure, returns an error message.
        :rtype: dict
        """
        body = { 'PlutusTransactionReferenceID': data['plutusTransactionReferenceID'] }
        response = call_pine_labs(payment_method=self, endpoint='GetCloudBasedTxnStatus', payload=body)
        if response.get('ResponseCode') in [0, 1001]:
            formatted_transaction_data = { d['Tag']: d['Value'] for d in response['TransactionData'] } if response.get('ResponseCode') == 0 else {}
            return {
                'responseCode': response['ResponseCode'],
                'status': response['ResponseMessage'],
                'plutusTransactionReferenceID': response['PlutusTransactionReferenceID'],
                'data': formatted_transaction_data,
            }
        default_error = _('The expected error code for the Pine Labs POS status request was not included in the response.')
        error = response.get('ResponseMessage') or response.get('errorMessage') or default_error
        return {'error': error}

    def pine_labs_cancel_payment_request(self, data):
        """
        Cancels a payment request via Pine Labs POS API.

        :param dict data: Contains `amount` and `plutusTransactionReferenceID`.
        :return: Success response with `responseCode` and `notification` or error with `errorMessage`.
        :rtype: dict
        """
        body = {
            'Amount': data['amount'],
            'PlutusTransactionReferenceID': data['plutusTransactionReferenceID'],
            'TakeToHomeScreen': True,
            'ConfirmationRequired': True
        }
        response = call_pine_labs(payment_method=self, endpoint='CancelTransactionForced', payload=body)
        if response.get('ResponseCode') == 0 and response.get('ResponseMessage') == "APPROVED":
            return {
                'responseCode': response['ResponseCode'],
                'notification': _('Pine Labs POS transaction cancelled. Retry again for collecting payment.')
            }
        default_error = _('The expected error code for the Pine Labs POS status request was not included in the response.')
        error = response.get('ResponseMessage') or response.get('errorMessage') or default_error
        return { 'error': error }

    @api.constrains('use_payment_terminal')
    def _check_pine_labs_terminal(self):
        if any(record.use_payment_terminal == 'pine_labs' and record.company_id.currency_id.name != 'INR' for record in self):
            raise UserError(_('This Payment Terminal is only valid for INR Currency'))
