from requests.exceptions import RequestException
from threading import Timer

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
        return {"error": error}

    def pinelabs_fetch_payment_status(self, data):
        pinelabs = PinelabsPosRequest(self)
        body = pinelabs._pinelabs_request_body(payment_mode=False)
        body.update({'PlutusTransactionReferenceID': data.get('plutusTransactionReferenceID')})

        retry_count = 0
        def get_status():
            nonlocal retry_count
            with self.pool.cursor() as cr:
                new_env = self.env(cr=cr)
                config = new_env["pos.config"].browse(data.get("config_id"))
                payment_method = new_env["pos.payment.method"].browse(data.get("payment_method_id"))
                try:
                    response = pinelabs._call_pinelabs(endpoint='GetCloudBasedTxnStatus', payload=body)
                    if response.get('ResponseCode') == 1001:
                        if retry_count <= MAX_RETRIES:
                            retry_count += 1
                            Timer(5, get_status).start()
                        else:
                            # We automatically cancel transactions in cases of inactivity.
                            error = _("The transaction has failed due to inactivity")
                            payment_method.pinelabs_cancel_payment_request(data)
                            config._notify("PINELABS_PAYMENT_RESPONSE", {"error": error})
                    elif response.get('ResponseCode') == 0:
                        pinelabs_latest_response = {
                            'responseCode': response.get('ResponseCode'),
                            'status': response.get('ResponseMessage'),
                            'plutusTransactionReferenceID': response.get('PlutusTransactionReferenceID'),
                            'data': format_transaction_data(response.get('TransactionData'))
                        }
                        config._notify("PINELABS_PAYMENT_RESPONSE", pinelabs_latest_response)
                    else:
                        default_error_msg = _('The expected error code for the Pine Labs POS payment status request was not included in the response.')
                        error = PINELABS_ERROR_CODES_MAPPING.get(response.get('ResponseMessage'))[1] or response.get('ResponseMessage') or default_error_msg
                        config._notify("PINELABS_PAYMENT_RESPONSE", {"error": error})

                except RequestException as e:
                    error_msg = _('A request error occurred while checking Pine Labs POS payment status.')
                    payment_method.pinelabs_latest_response = {"error": error}
                    config._notify("PINELABS_PAYMENT_RESPONSE", {"error": error_msg})

        get_status()

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
                "responseCode": response.get('ResponseCode'),
                "error": _("Pine Labs POS transaction cancelled successfully")
            }
        default_error_msg = _('The expected error code for the Pine Labs POS payment cancellation request was not included in the response.')
        errorMessage = PINELABS_ERROR_CODES_MAPPING.get(response.get('ResponseMessage'))[1] or response.get('ResponseMessage') or default_error_msg
        return {
            "responseCode": PINELABS_ERROR_CODES_MAPPING.get(response.get('ResponseMessage'))[0] or response.get('ResponseCode'),
            "errorMessage": errorMessage
        }

    @api.constrains('use_payment_terminal')
    def _check_pinelabs_terminal(self):
        if any(record.use_payment_terminal == 'pinelabs' and record.company_id.currency_id.name != 'INR' for record in self):
            raise UserError(_('This Payment Terminal is only valid for INR Currency'))


def format_transaction_data(transaction_data):
    return { d['Tag']: d['Value'] for d in transaction_data }
