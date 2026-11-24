from odoo import api, fields, models,  _
from odoo.exceptions import UserError
from odoo.tools import consteq, hmac

from .pine_labs_pos_request import call_pine_labs


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    pine_labs_merchant = fields.Char(string='Pine Labs Merchant ID', help='A merchant id issued directly to the merchant by Pine Labs.', copy=False)
    pine_labs_store = fields.Char(string='Pine Labs Store ID', help='A store id issued directly to the merchant by Pine Labs.', copy=False)
    pine_labs_client = fields.Char(string='Pine Labs Client ID', help='A client id issued directly to the merchant by Pine Labs.', copy=False)
    pine_labs_security_token = fields.Char(string='Pine Labs Security Token', help='A security token issued directly to the merchant by Pine Labs.', groups="point_of_sale.group_pos_manager")
    pine_labs_allowed_payment_mode = fields.Selection(
        selection=[('all', "All"), ('card', "Card"), ('upi', "Upi")],
        string='Pine Labs Allowed Payment Modes',
        help='Accepted payment modes by Pine Labs for transactions.')
    pine_labs_test_mode = fields.Boolean(string='Pine Labs Test Mode', help='Test Pine Labs transaction process.')

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('pine_labs', 'Pine Labs')]

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
            plutus_transaction_ref = response['PlutusTransactionReferenceID']
            return {
                'responseCode': response['ResponseCode'],
                'status': response['ResponseMessage'],
                'plutusTransactionReferenceID': plutus_transaction_ref,
                'signature': self._pine_labs_sign_transaction(plutus_transaction_ref, data['transactionNumber'], data['amount']),
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

    @api.constrains('payment_provider')
    def _check_pine_labs_terminal(self):
        if any(record.payment_provider == 'pine_labs' and record.company_id.currency_id.name != 'INR' for record in self):
            raise UserError(_('This Payment Terminal is only valid for INR Currency'))

    @api.model
    def _allowed_actions_in_self_order(self):
        return super()._allowed_actions_in_self_order() + ['pine_labs_make_payment_request', 'pine_labs_fetch_payment_status', 'pine_labs_cancel_payment_request']

    def _pine_labs_sign_transaction(self, plutus_transaction_ref, transaction_number, amount):
        # Pine Labs approves the status of any valid Plutus reference, whatever it
        # was issued for, so the signature proves which transaction number and
        # amount (in paisa) a Plutus reference was issued for.
        return hmac(self.env(su=True), 'pos_pine_labs', f'{plutus_transaction_ref}/{transaction_number}/{float(amount)}')

    def _is_valid_self_order_payment(self, pos_config, order, payment):
        if self.payment_provider != 'pine_labs':
            return super()._is_valid_self_order_payment(pos_config, order, payment)
        plutus_transaction_ref = str(payment.get('pine_labs_plutus_transaction_ref') or '')
        # Same transaction number as `_processPineLabs` builds for the only payment
        # of a kiosk order: `payment['amount']` is the JSON number sent by the
        # frontend, so `str()` formats it as the frontend does.
        transaction_number = f"{pos_config.id}/{order['uuid']}/{self.id}/{pos_config.currency_id.name}/{payment['amount']}/1"
        expected_signature = self._pine_labs_sign_transaction(plutus_transaction_ref, transaction_number, float(payment['amount']) * 100)
        if not plutus_transaction_ref or not consteq(str(payment.get('pine_labs_signature') or ''), expected_signature):
            return False
        if self.env['pos.payment'].search_count([
            ('payment_method_id', '=', self.id),
            ('pine_labs_plutus_transaction_ref', '=', plutus_transaction_ref),
        ], limit=1):
            return False
        status = self.pine_labs_fetch_payment_status({'plutusTransactionReferenceID': plutus_transaction_ref})
        return status.get('status') == 'TXN APPROVED' and str(status.get('plutusTransactionReferenceID')) == plutus_transaction_ref
