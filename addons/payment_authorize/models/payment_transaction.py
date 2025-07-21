# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo import _, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_authorize import const
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as provider-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'authorize':
            return super()._get_specific_processing_values(processing_values)

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
        """Override of `payment` to send a payment request to Authorize."""
        if self.provider_code != 'authorize':
            return super()._send_payment_request()

        authorize_API = AuthorizeAPI(self.provider_id)
        if self.provider_id.capture_manually:
            res_content = authorize_API.authorize(self, token=self.token_id)
            _logger.info(
                "authorize request response for transaction %s:\n%s",
                self.reference, pprint.pformat(res_content)
            )
        else:
            res_content = authorize_API.auth_and_capture(self, token=self.token_id)
            _logger.info(
                "auth_and_capture request response for transaction %s:\n%s",
                self.reference, pprint.pformat(res_content)
            )
        self._process('authorize', {'response': res_content})

    def _send_refund_request(self):
        """Override of `payment` to send a refund request to Authorize."""
        if self.provider_code != 'authorize':
            return super()._send_refund_request()

        authorize_api = AuthorizeAPI(self.provider_id)
        tx_details = authorize_api.get_transaction_details(
            self.source_transaction_id.provider_reference
        )
        if 'err_code' in tx_details:  # Could not retrieve the transaction details.
            self._set_error(_(
                "Could not retrieve the transaction details. (error code: %(error_code)s; error_details: %(error_message)s)",
                error_code=tx_details['err_code'], error_message=tx_details.get('err_msg'),
            ))
            return

        tx_status = tx_details.get('transaction', {}).get('transactionStatus')
        if tx_status in const.TRANSACTION_STATUS_MAPPING['voided']:
            # The payment has been voided from Authorize.net side before we could refund it.
            self._set_canceled(extra_allowed_states=('done',))
        elif tx_status in const.TRANSACTION_STATUS_MAPPING['refunded']:
            # The payment has been refunded from Authorize.net side before we could refund it. We
            # create a refund tx on Odoo to reflect the move of the funds.
            self._set_done()
            # Immediately post-process the transaction as the post-processing will not be
            # triggered by a customer browsing the transaction from the portal.
            self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif any(tx_status in const.TRANSACTION_STATUS_MAPPING[k] for k in ('authorized', 'captured')):
            if tx_status in const.TRANSACTION_STATUS_MAPPING['authorized']:
                # The payment has not been settled on Authorize.net yet. It must be voided rather
                # than refunded. Since the funds have not moved yet, we don't create a refund tx.
                res_content = authorize_api.void(self.source_transaction_id.provider_reference)
            else:
                # The payment has been settled on Authorize.net side. We can refund it.
                rounded_amount = round(self.amount, self.currency_id.decimal_places)
                res_content = authorize_api.refund(
                    self.provider_reference, rounded_amount, tx_details
                )
            _logger.info(
                "refund request response for transaction %s:\n%s",
                self.reference, pprint.pformat(res_content)
            )
            data = {'reference': self.reference, 'response': res_content}
            self._process('authorize', data)
        else:
            err_msg = _(
                "The transaction is not in a status to be refunded."
                " (status: %(status)s, details: %(message)s)",
                status=tx_status, message=tx_details.get('messages', {}).get('message'),
            )
            _logger.warning(err_msg)
            self._set_error(err_msg)

    def _send_capture_request(self):
        """Override of `payment` to send a capture request to Authorize."""
        if self.provider_code != 'authorize':
            return super()._send_capture_request()

        authorize_API = AuthorizeAPI(self.provider_id)
        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        res_content = authorize_API.capture(
            self.source_transaction_id.provider_reference, rounded_amount
        )
        _logger.info(
            "capture request response for transaction %s:\n%s",
            self.reference, pprint.pformat(res_content)
        )
        self._process('authorize', {'response': res_content})

    def _send_void_request(self):
        """Override of `payment` to send a void request to Authorize."""
        if self.provider_code != 'authorize':
            return super()._send_void_request()

        authorize_API = AuthorizeAPI(self.provider_id)
        res_content = authorize_API.void(self.provider_reference)
        _logger.info(
            "void request response for transaction %s:\n%s",
            self.reference, pprint.pformat(res_content)
        )
        self._process('authorize', {'response': res_content})

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'authorize':
            return super()._extract_amount_data(payment_data)

        tx_details = AuthorizeAPI(self.provider_id).get_transaction_details(
            payment_data.get('response', {}).get('x_trans_id')
        )
        amount = tx_details.get('transaction', {}).get('authAmount')
        # Authorize supports only one currency per account.
        currency = self.provider_id.available_currency_ids  # The currency has not been removed from the provider.
        return {
            'amount': float(amount),
            'currency_code': currency.name,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'authorize':
            return super()._apply_updates(payment_data)

        response_content = payment_data.get('response')

        # Update the provider reference.
        self.provider_reference = response_content.get('x_trans_id')

        # Update the payment method.
        payment_method_code = response_content.get('payment_method_code', '').lower()
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status_code = response_content.get('x_response_code', '3')
        if status_code == '1':  # Approved
            status_type = response_content.get('x_type').lower()
            if status_type in ('auth_capture', 'prior_auth_capture'):
                self._set_done()
            elif status_type == 'auth_only':
                self._set_authorized()
                if self.operation == 'validation':
                    self._void()  # In last step because it processes the response.
            elif status_type == 'void':
                if self.operation == 'validation':  # Validation txs are authorized and then voided
                    self._set_done()  # If the refund went through, the validation tx is confirmed
                else:
                    self._set_canceled(extra_allowed_states=('done',))
            elif status_type == 'refund' and self.operation == 'refund':
                self._set_done()
                # Immediately post-process the transaction as the post-processing will not be
                # triggered by a customer browsing the transaction from the portal.
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif status_code == '2':  # Declined
            self._set_canceled(state_message=response_content.get('x_response_reason_text'))
        elif status_code == '4':  # Held for Review
            self._set_pending()
        else:  # Error / Unknown code
            error_code = response_content.get('x_response_reason_text')
            _logger.info(
                "Received data with invalid status (%(status)s) and error code (%(err)s) for "
                "transaction %(ref)s.",
                {
                    'status': status_code,
                    'err': error_code,
                    'ref': self.reference,
                },
            )
            self._set_error(_(
                "Received data with status code \"%(status)s\" and error code \"%(error)s\".",
                status=status_code, error=error_code
            ))

    def _extract_token_values(self, payment_data):
        """Override of `payment` to extract the token values from the payment data."""
        if self.provider_code != 'authorize':
            return super()._extract_token_values(payment_data)

        if self.token_id:
            return {}

        authorize_API = AuthorizeAPI(self.provider_id)
        cust_profile = authorize_API.create_customer_profile(
            self.partner_id, self.provider_reference
        )
        _logger.info(
            "create_customer_profile request response for transaction %s:\n%s",
            self.reference, pprint.pformat(cust_profile)
        )
        if not cust_profile or 'payment_profile_id' not in cust_profile:  # Failed to fetch data.
            return {}

        return {
            'payment_details': cust_profile.get('payment_details'),
            'provider_ref': cust_profile['payment_profile_id'],
            'authorize_profile': cust_profile.get('profile_id'),
        }
