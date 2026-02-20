# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import datetime

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import hash_sign

TIMEOUT = 10


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # Credentials from Mpesa
    consumer_key = fields.Char(string="Consumer Key")
    consumer_secret = fields.Char(string="Consumer Secret")
    business_short_code = fields.Char(string="Business Short Code")
    passkey = fields.Char(string="Passkey", help="The passkey is used to generate the password for the STK Push")
    safaricom_test_mode = fields.Boolean(string="Test Mode", default=True, help="Use sandbox environment")
    safaricom_payment_type = fields.Selection(
        selection=[('mpesa_express', 'M-PESA Express'), ('lipa_na_mpesa', 'Lipa na M-PESA')],
        string="Payment Type",
        default='mpesa_express',
    )

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('safaricom', 'M-Pesa')]

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically register URLs for Lipa na M-PESA payment methods"""
        payment_methods = super().create(vals_list)

        for payment_method in payment_methods:
            if (payment_method.use_payment_terminal == 'safaricom' and payment_method.safaricom_payment_type == 'lipa_na_mpesa'):
                payment_method.lipa_na_mpesa_register_urls()

        return payment_methods

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['safaricom_test_mode', 'safaricom_payment_type', 'business_short_code']
        return params

    def _get_express_stkpush_endpoint(self):
        """STK Push endpoint"""
        if self.safaricom_test_mode:
            return 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        return 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'

    def _get_oauth_endpoint(self):
        """OAuth endpoint to get access token"""
        if self.safaricom_test_mode:
            return 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        return 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

    def _get_lipa_na_mpesa_register_endpoint(self):
        if self.safaricom_test_mode:
            return 'https://sandbox.safaricom.co.ke/mpesa/c2b/v2/registerurl'
        return 'https://api.safaricom.co.ke/mpesa/c2b/v2/registerurl'

    def _get_qr_code_endpoint(self):
        if self.safaricom_test_mode:
            return 'https://sandbox.safaricom.co.ke/mpesa/qrcode/v1/generate'
        return 'https://api.safaricom.co.ke/mpesa/qrcode/v1/generate'

    def bearer_token(self):
        """Get OAuth access token"""
        self.ensure_one()

        if not self.consumer_key or not self.consumer_secret:
            raise UserError(_("Consumer Key and Consumer Secret are required for Safaricom M-Pesa"))

        try:
            consumer_key = self.consumer_key.strip() if self.consumer_key else ''
            consumer_secret = self.consumer_secret.strip() if self.consumer_secret else ''

            auth = requests.auth.HTTPBasicAuth(consumer_key, consumer_secret)
            response = requests.get(self._get_oauth_endpoint(), auth=auth, timeout=TIMEOUT)

            response.raise_for_status()

            data = response.json()
            access_token = data.get('access_token')

            if not access_token:
                raise UserError(_("Failed to retrieve access token from Safaricom"))

            return access_token

        except requests.exceptions.RequestException:
            raise UserError(_("Failed to retrieve access token from Safaricom"))

    def _get_password(self, timestamp):
        """Generate password for STK Push"""
        return base64.b64encode(f"{self.business_short_code}{self.passkey}{timestamp}".encode()).decode()

    def _format_phone_number(self, phone):
        """Format phone number to Safaricom format (254XXXXXXXXX)"""
        phone = ''.join(filter(str.isdigit, phone)).lstrip('0')

        # Add country code if not present
        if not phone.startswith('254'):
            phone = '254' + phone
        return phone

    def mpesa_express_send_payment_request(self, data):
        """Send STK Push payment request to customer's phone"""
        self.ensure_one()

        try:
            access_token = self.bearer_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._get_password(timestamp)

            phone_number = self._format_phone_number(data.get('phone_number', ''))

            if not phone_number:
                return {'error': _("Invalid phone number format. Please use format: 2547XXXXXXXX")}

            signed_hash_payload = hash_sign(self.sudo().env, "pos_safaricom", {"payment_method_id": self.id}, expiration_hours=6)

            payload = {
                'BusinessShortCode': self.business_short_code,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(data.get('amount', 0)),
                'PartyA': phone_number,
                'PartyB': self.business_short_code,
                'PhoneNumber': phone_number,
                'CallBackURL': f"{self.get_base_url()}/pos_safaricom/callback?payload={signed_hash_payload}",
                'AccountReference': data.get('account_reference', 'POS Payment'),
                'TransactionDesc': data.get('transaction_desc', 'Payment'),
                }

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }

            response = requests.post(
                self._get_express_stkpush_endpoint(),
                json=payload,
                headers=headers,
                timeout=TIMEOUT,
            )

            result = response.json()

            if result.get('ResponseCode') == '0':
                return {
                    'success': False,  # Not successful yet, waiting for customer confirmation
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'message': result.get('CustomerMessage', 'Payment request sent to customer phone'),
                }

            return {
                'error': result.get('errorMessage') or result.get('CustomerMessage', 'Payment request failed'),
            }

        except (requests.exceptions.RequestException, ValueError) as e:
            return {'error': e}

    def retrieve_payment_status(self, merchant_request_id, checkout_request_id, result_code, result_desc, callback_metadata=None):
        """Process payment status from callback and notify POS sessions"""
        self.ensure_one()

        payment_successful = (result_code == 0)

        payment_data = {
            'merchant_request_id': merchant_request_id,
            'checkout_request_id': checkout_request_id,
            'result_code': result_code,
            'result_desc': result_desc,
            'success': payment_successful,
        }

        if payment_successful and callback_metadata:
            metadata_items = callback_metadata.get('Item', [])
            for item in metadata_items:
                name = item.get('Name')
                value = item.get('Value')

                if name == 'Amount':
                    payment_data['amount'] = value
                elif name == 'MpesaReceiptNumber':
                    payment_data['transaction_id'] = value
                elif name == 'TransactionDate':
                    payment_data['transaction_date'] = str(value)
                elif name == 'PhoneNumber':
                    payment_data['phone_number'] = str(value)

        # Notify all active POS sessions using this payment method
        active_sessions = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('config_id.payment_method_ids', 'in', self.ids),
        ])

        for pos_session in active_sessions:
            pos_session.config_id._notify('SAFARICOM_LATEST_RESPONSE', {
                'merchant_request_id': payment_data.get('merchant_request_id'),
                'checkout_request_id': payment_data.get('checkout_request_id'),
                'success': payment_data.get('success', False),
                'transaction_id': payment_data.get('transaction_id', ''),
                'phone_number': payment_data.get('phone_number', ''),
                'amount': payment_data.get('amount', 0),
                'result_desc': payment_data.get('result_desc', ''),
            })
        return payment_data

    def lipa_na_mpesa_register_urls(self):
        """
        Register C2B URLs for Lipa na M-PESA
        The ValidationURL is the URL that will be called to validate the payment before charges the customer if business has activated it.
        The ConfirmationURL is the URL that will be called when the payment is successful or unsuccessful.
        The ResponseType is set to Completed to charge the customer even if the ValidationURL returns an error or is unreachable.

        This is a one-time API call. URLs should only be registered once unless force_register is True.
        """
        self.ensure_one()

        try:
            access_token = self.bearer_token()

            payload_hash = {
                "payment_method_id": self.id,
            }

            signed_hash_payload = hash_sign(self.sudo().env, "pos_safaricom", payload_hash, expiration_hours=6)

            payload = {
                'ShortCode': self.business_short_code,
                'ResponseType': 'Completed',
                'ValidationURL': f"{self.get_base_url()}/c2b/validation/callback?payload={signed_hash_payload}",
                'ConfirmationURL': f"{self.get_base_url()}/c2b/confirmation/callback?payload={signed_hash_payload}",
            }

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }

            response = requests.post(
                self._get_lipa_na_mpesa_register_endpoint(),
                json=payload,
                headers=headers,
                timeout=TIMEOUT,
            )
            result = response.json()

            if result.get('ResponseCode') != '00000000':
                raise UserError(_("Failed to register URLs"))

        except (requests.exceptions.RequestException, ValueError):
            raise UserError(_("Failed to register URLs. Check your credentials and try again."))

    def create_payment_transaction(self, trans_id, trans_amount, msisdn, name):
        """Create a payment transaction for the payment"""
        self.ensure_one()

        if (self.env['transaction.lipa.na.mpesa'].search([('trans_id', '=', trans_id)])):
            return

        self.env['transaction.lipa.na.mpesa'].create({
            'trans_id': trans_id,
            'name': name,
            'number': msisdn,
            'amount': int(float(trans_amount)),
            'received_at': datetime.now(),
        })

        for pos_config in self.config_ids:
            pos_config._notify('NEW_LIPA_NA_MPESA_TRANSACTION', {})

    def mark_transaction_used(self, transaction_id):
        """Mark a transaction as used by deleting it or updating its status"""
        self.ensure_one()

        transaction = self.env['transaction.lipa.na.mpesa'].browse(transaction_id)
        if transaction.exists():
            transaction.unlink()

    def generate_qr_code(self, data):
        """Generate QR Code for Lipa na M-PESA with all informations needed to pay"""
        self.ensure_one()

        try:
            access_token = self.bearer_token()

            body = {
                'MerchantName': data.get('name', self.company_id.name),
                'RefNo': data.get('ref', ''),
                'Amount': data.get('amount', 0),
                'TrxCode': data.get('trxCode', 'BG'),
                'CPI': data.get('cpi', self.business_short_code),
                'Size': data.get('size', '300'),
            }

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }

            response = requests.post(
                self._get_qr_code_endpoint(),
                json=body,
                headers=headers,
                timeout=TIMEOUT,
            )

            result = response.json()

            qr_code = result.get('QRCode')
            if not qr_code:
                error_msg = result.get('errorMessage', 'No QR Code in response')
                return {'error': error_msg}

            return qr_code

        except (requests.exceptions.RequestException, ValueError) as e:
            return {'error': e}
