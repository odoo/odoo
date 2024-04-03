# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI
from odoo.addons.payment_authorize.const import TRANSACTION_STATUS_MAPPING


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as provider-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'authorize':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }

    def _authorize_create_transaction_request(self, opaque_data):
        """ Create an Authorize.Net payment transaction request.

        Note: self.ensure_one()

        :param dict opaque_data: The payment details obfuscated by Authorize.Net
        :return:
        """
        self.ensure_one()

        authorize_API = AuthorizeAPI(self.provider_id)
        if self.provider_id.capture_manually or self.operation == 'validation':
            return authorize_API.authorize(self, opaque_data=opaque_data)
        else:
            return authorize_API.auth_and_capture(self, opaque_data=opaque_data)

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Authorize.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'authorize':
            return

        if not self.token_id.authorize_profile:
            raise UserError("Authorize.Net: " + _("The transaction is not linked to a token."))

        authorize_API = AuthorizeAPI(self.provider_id)
        if self.provider_id.capture_manually:
            res_content = authorize_API.authorize(self, token=self.token_id)
            _logger.info(
                "authorize request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(res_content)
            )
        else:
            res_content = authorize_API.auth_and_capture(self, token=self.token_id)
            _logger.info(
                "auth_and_capture request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(res_content)
            )
        self._handle_notification_data('authorize', {'response': res_content})

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of payment to send a refund request to Authorize.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        self.ensure_one()

        if self.provider_code != 'authorize':
            return super()._send_refund_request(amount_to_refund=amount_to_refund)

        authorize_api = AuthorizeAPI(self.provider_id)
        tx_details = authorize_api.get_transaction_details(self.provider_reference)
        if 'err_code' in tx_details:  # Could not retrieve the transaction details.
            raise ValidationError("Authorize.Net: " + _(
                "Could not retrieve the transaction details. (error code: %s; error_details: %s)",
                tx_details['err_code'], tx_details.get('err_msg')
            ))

        refund_tx = self.env['payment.transaction']
        tx_status = tx_details.get('transaction', {}).get('transactionStatus')
        if tx_status in TRANSACTION_STATUS_MAPPING['voided']:
            # The payment has been voided from Authorize.net side before we could refund it.
            self._set_canceled()
        elif tx_status in TRANSACTION_STATUS_MAPPING['refunded']:
            # The payment has been refunded from Authorize.net side before we could refund it. We
            # create a refund tx on Odoo to reflect the move of the funds.
            refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
            refund_tx._set_done()
            # Immediately post-process the transaction as the post-processing will not be
            # triggered by a customer browsing the transaction from the portal.
            self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif any(tx_status in TRANSACTION_STATUS_MAPPING[k] for k in ('authorized', 'captured')):
            if tx_status in TRANSACTION_STATUS_MAPPING['authorized']:
                # The payment has not been settle on Authorize.net yet. It must be voided rather
                # than refunded. Since the funds have not moved yet, we don't create a refund tx.
                res_content = authorize_api.void(self.provider_reference)
                tx_to_process = self
            else:
                # The payment has been settled on Authorize.net side. We can refund it.
                refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
                rounded_amount = round(amount_to_refund, self.currency_id.decimal_places)
                res_content = authorize_api.refund(
                    self.provider_reference, rounded_amount, tx_details
                )
                tx_to_process = refund_tx
            _logger.info(
                "refund request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(res_content)
            )
            data = {'reference': tx_to_process.reference, 'response': res_content}
            tx_to_process._handle_notification_data('authorize', data)
        else:
            raise ValidationError("Authorize.net: " + _(
                "The transaction is not in a status to be refunded. (status: %s, details: %s)",
                tx_status, tx_details.get('messages', {}).get('message')
            ))
        return refund_tx

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider_code != 'authorize':
            return

        authorize_API = AuthorizeAPI(self.provider_id)
        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        res_content = authorize_API.capture(self.provider_reference, rounded_amount)
        _logger.info(
            "capture request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(res_content)
        )
        self._handle_notification_data('authorize', {'response': res_content})

    def _send_void_request(self):
        """ Override of payment to send a void request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'authorize':
            return

        authorize_API = AuthorizeAPI(self.provider_id)
        res_content = authorize_API.void(self.provider_reference)
        _logger.info(
            "void request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(res_content)
        )
        self._handle_notification_data('authorize', {'response': res_content})

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Find the transaction based on Authorize.net data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'authorize' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'authorize')])
        if not tx:
            raise ValidationError(
                "Authorize.Net: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Authorize data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'authorize':
            return

        response_content = notification_data.get('response')

        self.provider_reference = response_content.get('x_trans_id')
        status_code = response_content.get('x_response_code', '3')
        if status_code == '1':  # Approved
            status_type = response_content.get('x_type').lower()
            if status_type in ('auth_capture', 'prior_auth_capture'):
                self._set_done()
                if self.tokenize and not self.token_id:
                    self._authorize_tokenize()
            elif status_type == 'auth_only':
                self._set_authorized()
                if self.tokenize and not self.token_id:
                    self._authorize_tokenize()
                if self.operation == 'validation':
                    self._send_void_request()  # In last step because it processes the response.
            elif status_type == 'void':
                if self.operation == 'validation':  # Validation txs are authorized and then voided
                    self._set_done()  # If the refund went through, the validation tx is confirmed
                else:
                    self._set_canceled()
            elif status_type == 'refund' and self.operation == 'refund':
                self._set_done()
                # Immediately post-process the transaction as the post-processing will not be
                # triggered by a customer browsing the transaction from the portal.
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif status_code == '2':  # Declined
            self._set_canceled()
        elif status_code == '4':  # Held for Review
            self._set_pending()
        else:  # Error / Unknown code
            error_code = response_content.get('x_response_reason_text')
            _logger.info(
                "received data with invalid status (%(status)s) and error code (%(err)s) for "
                "transaction with reference %(ref)s",
                {
                    'status': status_code,
                    'err': error_code,
                    'ref': self.reference,
                },
            )
            self._set_error(
                "Authorize.Net: " + _(
                    "Received data with status code \"%(status)s\" and error code \"%(error)s\"",
                    status=status_code, error=error_code
                )
            )

    def _authorize_tokenize(self):
        """ Create a token for the current transaction.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

        authorize_API = AuthorizeAPI(self.provider_id)
        cust_profile = authorize_API.create_customer_profile(
            self.partner_id, self.provider_reference
        )
        _logger.info(
            "create_customer_profile request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(cust_profile)
        )
        if cust_profile:
            token = self.env['payment.token'].create({
                'provider_id': self.provider_id.id,
                'payment_details': cust_profile.get('payment_details'),
                'partner_id': self.partner_id.id,
                'provider_ref': cust_profile.get('payment_profile_id'),
                'authorize_profile': cust_profile.get('profile_id'),
                'authorize_payment_method_type': self.provider_id.authorize_payment_method_type,
                'verified': True,
            })
            self.write({
                'token_id': token.id,
                'tokenize': False,
            })
            _logger.info(
                "created token with id %(token_id)s for partner with id %(partner_id)s from "
                "transaction with reference %(ref)s",
                {
                    'token_id': token.id,
                    'partner_id': self.partner_id.id,
                    'ref': self.reference,
                },
            )
