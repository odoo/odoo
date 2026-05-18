# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_payu import const as payu_consts
from odoo.addons.payment_payu import utils as payu_utils

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """Return PayU-specific values including headers for frontend."""
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'payu':
            return res
        # Raise Usererror because PayU doesn't send accurate error message and send some error occured
        if not self.partner_phone or not self.partner_email:
            raise UserError(self.env._('Invalid or missing Email or phone number.'))

        txn_env = 'test' if self.provider_id.state == 'test' else 'prod'
        payload_value = self._payu_prepare_txn_payload()
        return {**res, 'txn_env': txn_env, 'payload': payload_value}

    def _payu_prepare_txn_payload(self):
        """ Prepare the payload for the order request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        return_url = f'{self.provider_id.get_base_url()}{payu_consts.RETURN_URL}'
        webhook_url = f'{self.provider_id.get_base_url()}{payu_consts.WEBHOOK_URL}'
        pm_code = (self.payment_method_id.primary_payment_method_id or self.payment_method_id).code
        payu_pm_code = payu_consts.PAYMENT_METHODS_MAPPING.get(pm_code, [])
        show_payment_mode = '|'.join(payu_pm_code)
        payload = {
            'key': self.provider_id.payu_merchant_key,
            'txnid': self.reference,
            'amount': str(self.amount),
            'productinfo': 'Odoo-Product',
            'firstname': self.partner_name,
            'phone': self.partner_phone,
            'email': self.partner_email,
            'surl': return_url,
            'furl': return_url,
            'udf1': 'payment',
            'enforce_paymethod': show_payment_mode,
            'partner_webhook_success': webhook_url,
            'partner_webhook_failure': webhook_url,
            'salt': self.provider_id.payu_merchant_salt,  # Delete `salt` key after computing payload hash as it is not required in payload
        }
        payload['hash'] = payu_utils.generate_payu_hash(
            payload=payload,
            hash_sequence=payu_consts.PAYU_HASH_SEQUENCE.get('PAYMENT'),
        )
        payload.pop('salt', None)
        return payload

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'payu':
            return super()._apply_updates(payment_data)

        # Determine the webhook type based on the payload fields.
        if 'udf1' in payment_data and (payment_data.get('udf1') or '').strip() == 'payment':
            webhook_type = 'payment'
        elif 'action' in payment_data and (payment_data.get('action') or '').strip() == 'refund':
            webhook_type = 'refund'
        else:
            _logger.warning('Payu: Invalid operation type')
            return None

        allowed_to_modify = self.state not in ('done', 'authorized')

        if allowed_to_modify:
            self.provider_reference = (payment_data.get('mihpayid') or '').strip()

        entity_status = payment_data.get('status', '').strip()
        if not entity_status:
            raise ValidationError(self.env._('Payu: Received data with missing status.'))

        # Update the payment state.
        STATUS_MAPPING = payu_consts.PAYMENT_STATUS_MAPPING
        if entity_status in STATUS_MAPPING['done']:
            self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if webhook_type == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif entity_status in STATUS_MAPPING.get('pending', []):
            self._set_pending()
        elif entity_status in STATUS_MAPPING['error']:
            _logger.warning(
                'The transaction with reference %s underwent an error. Reason: %s',
                self.reference, payment_data.get('error_message'),
            )
            self._set_error(
                self.env._('An error occurred during the processing of your payment. Please try again.'),
            )
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                'Received data for transaction with reference %s with invalid payment status: %s',
                self.reference, entity_status,
            )
            self._set_error(
                self.env._('Payu: Received data with invalid status: %s', entity_status),
            )
        return None

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        """ Override of `payment` to find the transaction based on Payu data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict payment_data: The normalized notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """

        if provider_code != 'payu':
            return super()._search_by_reference(provider_code, payment_data)
        txnid_key = 'token' if 'action' in payment_data and (payment_data.get('action') or '').strip() == 'refund' else 'txnid'
        reference = (payment_data.get(txnid_key) or '').strip()
        return self.search([('reference', '=', reference), ('provider_code', '=', 'payu')])

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != 'payu':
            return super()._extract_amount_data(payment_data)
        amount_key = 'amt' if 'action' in payment_data and (payment_data.get('action') or '').strip() == 'refund' else 'amount'
        return {
            'amount': float((payment_data.get(amount_key) or '0').strip()),  # PayU only supports payment API
            'currency_code': 'INR',  # PayU doesn't provide currency code in webhook data. And this is constant as INR for all.
        }

    def _send_refund_request(self):
        """ Override of `payment` to send a refund request to PayU.

        Note: self.ensure_one()

        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        if self.provider_code != 'payu':
            return super()._send_refund_request()
        webhook_url = f'{self.provider_id.get_base_url()}{payu_consts.WEBHOOK_URL}'
        payload = {
            'key': self.provider_id.payu_merchant_key,
            'command': 'cancel_refund_transaction',
            'var1': self.source_transaction_id.provider_reference,
            'var2': self.reference,
            'var3': -(self.amount),
            'var5': webhook_url,
            'salt': self.provider_id.payu_merchant_salt,
        }

        hash_payload = payu_utils.generate_payu_hash(payload=payload, hash_sequence=payu_consts.PAYU_HASH_SEQUENCE.get('REFUND'))
        payload['hash'] = hash_payload

        try:
            self._send_api_request('POST', '/merchant/postservice?form=2', data=payload, mode='refund')
        except ValidationError as e:
            self._set_error(str(e))
