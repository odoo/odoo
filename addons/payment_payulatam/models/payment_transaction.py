# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_repr

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_payulatam.controllers.main import PayuLatamController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider, prefix=None, separator='-', **kwargs):
        """ Override of payment to ensure that PayU Latam requirements for references are satisfied.

        PayU Latam requirements for transaction are as follows:
        - References must be unique at provider level for a given merchant account.
          This is satisfied by singularizing the prefix with the current datetime. If two
          transactions are created simultaneously, `_compute_reference` ensures the uniqueness of
          references by suffixing a sequence number.

        :param str provider: The provider of the acquirer handling the transaction
        :param str prefix: The custom prefix used to compute the full reference
        :param str separator: The custom separator used to separate the prefix from the suffix
        :return: The unique reference for the transaction
        :rtype: str
        """
        if provider == 'payulatam':
            if not prefix:
                # If no prefix is provided, it could mean that a module has passed a kwarg intended
                # for the `_compute_reference_prefix` method, as it is only called if the prefix is
                # empty. We call it manually here because singularizing the prefix would generate a
                # default value if it was empty, hence preventing the method from ever being called
                # and the transaction from received a reference named after the related document.
                prefix = self.sudo()._compute_reference_prefix(
                    provider, separator, **kwargs
                ) or None
            prefix = payment_utils.singularize_reference_prefix(prefix=prefix, separator=separator)
        return super()._compute_reference(provider, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Payulatam-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'payulatam':
            return res

        api_url = 'https://checkout.payulatam.com/ppp-web-gateway-payu/' \
            if self.acquirer_id.state == 'enabled' \
            else 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/'
        payulatam_values = {
            'merchantId': self.acquirer_id.payulatam_merchant_id,
            'referenceCode': self.reference,
            'description': self.reference,
            'amount': float_repr(processing_values['amount'], self.currency_id.decimal_places or 2),
            'tax': 0,
            'taxReturnBase': 0,
            'currency': self.currency_id.name,
            'accountId': self.acquirer_id.payulatam_account_id,
            'buyerFullName': self.partner_name,
            'buyerEmail': self.partner_email,
            'responseUrl': urls.url_join(self.get_base_url(), PayuLatamController._return_url),
            'confirmationUrl': urls.url_join(self.get_base_url(), PayuLatamController._webhook_url),
            'api_url': api_url,
        }
        if self.acquirer_id.state != 'enabled':
            payulatam_values['test'] = 1
        payulatam_values['signature'] = self.acquirer_id._payulatam_generate_sign(
            payulatam_values, incoming=False
        )
        return payulatam_values

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Payulatam data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        :raise: ValidationError if the signature can not be verified
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'payulatam':
            return tx

        reference = data.get('referenceCode')
        sign = data.get('signature')
        if not reference or not sign:
            raise ValidationError(
                "PayU Latam: " + _(
                    "Received data with missing reference (%(ref)s) or sign (%(sign)s).",
                    ref=reference, sign=sign
                )
            )

        tx = self.search([('reference', '=', reference), ('provider', '=', 'payulatam')])
        if not tx:
            raise ValidationError(
                "PayU Latam: " + _("No transaction found matching reference %s.", reference)
            )

        # Verify signature
        sign_check = tx.acquirer_id._payulatam_generate_sign(data, incoming=True)
        if sign_check != sign:
            raise ValidationError(
                "PayU Latam: " + _(
                    "Invalid sign: received %(sign)s, computed %(check)s.",
                    sign=sign, check=sign_check
                )
            )

        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Payulatam data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        super()._process_feedback_data(data)
        if self.provider != 'payulatam':
            return

        self.acquirer_reference = data.get('transactionId')

        status = data.get('lapTransactionState')
        state_message = data.get('message')
        if status == 'PENDING':
            self._set_pending(state_message=state_message)
        elif status == 'APPROVED':
            self._set_done(state_message=state_message)
        elif status in ('EXPIRED', 'DECLINED'):
            self._set_canceled(state_message=state_message)
        else:
            _logger.warning(
                "received unrecognized payment state %s for transaction with reference %s",
                status, self.reference
            )
            self._set_error("PayU Latam: " + _("Invalid payment status."))
