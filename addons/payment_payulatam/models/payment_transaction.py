# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
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
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of payment to ensure that PayU Latam requirements for references are satisfied.

        PayU Latam requirements for transaction are as follows:
        - References must be unique at provider level for a given merchant account.
          This is satisfied by singularizing the prefix with the current datetime. If two
          transactions are created simultaneously, `_compute_reference` ensures the uniqueness of
          references by suffixing a sequence number.

        :param str provider_code: The code of the provider handling the transaction
        :param str prefix: The custom prefix used to compute the full reference
        :param str separator: The custom separator used to separate the prefix from the suffix
        :return: The unique reference for the transaction
        :rtype: str
        """
        if provider_code == 'payulatam':
            if not prefix:
                # If no prefix is provided, it could mean that a module has passed a kwarg intended
                # for the `_compute_reference_prefix` method, as it is only called if the prefix is
                # empty. We call it manually here because singularizing the prefix would generate a
                # default value if it was empty, hence preventing the method from ever being called
                # and the transaction from received a reference named after the related document.
                prefix = self.sudo()._compute_reference_prefix(
                    provider_code, separator, **kwargs
                ) or None
            prefix = payment_utils.singularize_reference_prefix(prefix=prefix, separator=separator)
        return super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Payulatam-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'payulatam':
            return res

        api_url = 'https://checkout.payulatam.com/ppp-web-gateway-payu/' \
            if self.provider_id.state == 'enabled' \
            else 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/'
        base_url = self.get_base_url()
        payulatam_values = {
            'merchantId': self.provider_id.payulatam_merchant_id,
            'referenceCode': self.reference,
            'description': self.reference,
            'amount': float_repr(processing_values['amount'], self.currency_id.decimal_places or 2),
            'tax': 0,
            'taxReturnBase': 0,
            'currency': self.currency_id.name,
            'accountId': self.provider_id.payulatam_account_id,
            'buyerFullName': self.partner_name,
            'buyerEmail': self.partner_email,
            'responseUrl': urls.url_join(base_url, PayuLatamController._return_url),
            'confirmationUrl': urls.url_join(base_url, PayuLatamController._webhook_url),
            'api_url': api_url,
        }
        if self.provider_id.state != 'enabled':
            payulatam_values['test'] = 1
        payulatam_values['signature'] = self.provider_id._payulatam_generate_sign(
            payulatam_values, incoming=False
        )
        return payulatam_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Payulatam data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'payulatam' or len(tx) == 1:
            return tx

        reference = notification_data.get('referenceCode')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'payulatam')])
        if not tx:
            raise ValidationError(
                "PayU Latam: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Payulatam data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'payulatam':
            return

        self.provider_reference = notification_data.get('transactionId')

        status = notification_data.get('lapTransactionState')
        state_message = notification_data.get('message')
        if status == 'PENDING':
            self._set_pending(state_message=state_message)
        elif status == 'APPROVED':
            self._set_done(state_message=state_message)
        elif status in ('EXPIRED', 'DECLINED'):
            self._set_canceled(state_message=state_message)
        else:
            _logger.warning(
                "received data with invalid payment status (%s) for transaction with reference %s",
                status, self.reference
            )
            self._set_error("PayU Latam: " + _("Invalid payment status."))
