# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_flutterwave.const import PAYMENT_STATUS_MAPPING
from odoo.addons.payment_flutterwave.controllers.main import FlutterwaveController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Flutterwave-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'flutterwave':
            return res

        # Initiate the payment and retrieve the payment link data.
        base_url = self.provider_id.get_base_url()
        payload = {
            'tx_ref': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'redirect_url': urls.url_join(base_url, FlutterwaveController._return_url),
            'customer': {
                'email': self.partner_email,
                'name': self.partner_name,
                'phonenumber': self.partner_phone,
            },
            'customizations': {
                'title': self.company_id.name,
                'logo': urls.url_join(base_url, f'web/image/res.company/{self.company_id.id}/logo'),
            },
        }
        payment_link_data = self.provider_id._flutterwave_make_request('payments', payload=payload)

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values = {
            'api_url': payment_link_data['data']['link'],
        }
        return rendering_values

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Flutterwave.

        Note: self.ensure_one()

        :return: None
        :raise UserError: If the transaction is not linked to a token.
        """
        super()._send_payment_request()
        if self.provider_code != 'flutterwave':
            return

        # Prepare the payment request to Flutterwave.
        if not self.token_id:
            raise UserError("Flutterwave: " + _("The transaction is not linked to a token."))

        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        data = {
            'token': self.token_id.provider_ref,
            'email': self.token_id.flutterwave_customer_email,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'country': self.company_id.country_id.code,
            'tx_ref': self.reference,
            'first_name': first_name,
            'last_name': last_name,
            'ip': payment_utils.get_customer_ip_address(),
        }

        # Make the payment request to Flutterwave.
        response_content = self.provider_id._flutterwave_make_request(
            'tokenized-charges', payload=data
        )

        # Handle the payment request response.
        _logger.info(
            "payment request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        self._handle_notification_data('flutterwave', response_content['data'])

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Flutterwave data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'flutterwave' or len(tx) == 1:
            return tx

        reference = notification_data.get('tx_ref')
        if not reference:
            raise ValidationError("Flutterwave: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'flutterwave')])
        if not tx:
            raise ValidationError(
                "Flutterwave: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Flutterwave data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'flutterwave':
            return

        # Verify the notification data.
        verification_response_content = self.provider_id._flutterwave_make_request(
            'transactions/verify_by_reference', payload={'tx_ref': self.reference}, method='GET'
        )
        verified_data = verification_response_content['data']

        # Process the verified notification data.
        self.provider_reference = verified_data['id']
        payment_status = verified_data['status'].lower()
        if payment_status in PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
            has_token_data = 'token' in verified_data.get('card', {})
            if self.tokenize and has_token_data:
                self._flutterwave_tokenize_from_notification_data(verified_data)
        elif payment_status in PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "An error occurred during the processing of your payment (status %s). Please try "
                "again.", payment_status
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction with reference %s.",
                payment_status, self.reference
            )
            self._set_error("Flutterwave: " + _("Unknown payment status: %s", payment_status))

    def _flutterwave_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        self.ensure_one()

        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_details': notification_data['card']['last_4digits'],
            'partner_id': self.partner_id.id,
            'provider_ref': notification_data['card']['token'],
            'flutterwave_customer_email': notification_data['customer']['email'],
            'verified': True,  # The payment is confirmed, so the payment method is valid.
        })
        self.write({
            'token_id': token,
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
