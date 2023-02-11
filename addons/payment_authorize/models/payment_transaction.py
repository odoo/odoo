# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from .authorize_request import AuthorizeAPI
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as acquirer-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'authorize':
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

        authorize_API = AuthorizeAPI(self.acquirer_id)
        if self.acquirer_id.capture_manually or self.operation == 'validation':
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
        if self.provider != 'authorize':
            return

        if not self.token_id.authorize_profile:
            raise UserError("Authorize.Net: " + _("The transaction is not linked to a token."))

        authorize_API = AuthorizeAPI(self.acquirer_id)
        if self.acquirer_id.capture_manually:
            res_content = authorize_API.authorize(self, token=self.token_id)
            _logger.info("authorize request response:\n%s", pprint.pformat(res_content))
        else:
            res_content = authorize_API.auth_and_capture(self, token=self.token_id)
            _logger.info("auth_and_capture request response:\n%s", pprint.pformat(res_content))

        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_feedback_data('authorize', feedback_data)

    def _send_refund_request(self, amount_to_refund=None, create_refund_transaction=True):
        """ Override of payment to send a refund request to Authorize.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :param bool create_refund_transaction: Whether a refund transaction should be created or not
        :return: The refund transaction if any
        :rtype: recordset of `payment.transaction`
        """
        if self.provider != 'authorize':
            return super()._send_refund_request(
                amount_to_refund=amount_to_refund,
                create_refund_transaction=create_refund_transaction,
            )

        refund_tx = super()._send_refund_request(
            amount_to_refund=amount_to_refund, create_refund_transaction=False
        )

        authorize_API = AuthorizeAPI(self.acquirer_id)
        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        res_content = authorize_API.refund(self.acquirer_reference, rounded_amount)
        _logger.info("refund request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_feedback_data('authorize', feedback_data)

        return refund_tx

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider != 'authorize':
            return

        authorize_API = AuthorizeAPI(self.acquirer_id)
        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        res_content = authorize_API.capture(self.acquirer_reference, rounded_amount)
        _logger.info("capture request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_feedback_data('authorize', feedback_data)

    def _send_void_request(self):
        """ Override of payment to send a void request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider != 'authorize':
            return

        authorize_API = AuthorizeAPI(self.acquirer_id)
        res_content = authorize_API.void(self.acquirer_reference)
        _logger.info("void request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_feedback_data('authorize', feedback_data)

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Find the transaction based on the feedback data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the acquirer
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'authorize':
            return tx

        reference = data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider', '=', 'authorize')])
        if not tx:
            raise ValidationError(
                "Authorize.Net: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Authorize data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        super()._process_feedback_data(data)
        if self.provider != 'authorize':
            return

        response_content = data.get('response')

        self.acquirer_reference = response_content.get('x_trans_id')
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
                    # Void the transaction. In last step because it calls _handle_feedback_data()
                    self._send_refund_request(create_refund_transaction=False)
            elif status_type == 'void':
                if self.operation == 'validation':  # Validation txs are authorized and then voided
                    self._set_done()  # If the refund went through, the validation tx is confirmed
                else:
                    self._set_canceled()
        elif status_code == '2':  # Declined
            self._set_canceled()
        elif status_code == '4':  # Held for Review
            self._set_pending()
        else:  # Error / Unknown code
            error_code = response_content.get('x_response_reason_text')
            _logger.info(
                "received data with invalid status code %s and error code %s",
                status_code, error_code
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

        authorize_API = AuthorizeAPI(self.acquirer_id)
        cust_profile = authorize_API.create_customer_profile(
            self.partner_id, self.acquirer_reference
        )
        _logger.info("create_customer_profile request response:\n%s", pprint.pformat(cust_profile))
        if cust_profile:
            token = self.env['payment.token'].create({
                'acquirer_id': self.acquirer_id.id,
                'name': cust_profile.get('name'),
                'partner_id': self.partner_id.id,
                'acquirer_ref': cust_profile.get('payment_profile_id'),
                'authorize_profile': cust_profile.get('profile_id'),
                'authorize_payment_method_type': self.acquirer_id.authorize_payment_method_type,
                'verified': True,
            })
            self.write({
                'token_id': token.id,
                'tokenize': False,
            })
            _logger.info(
                "created token with id %s for partner with id %s", token.id, self.partner_id.id
            )
