# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_xendit import const


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Xendit-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'xendit':
            return res

        if self.currency_id.name in const.CURRENCY_DECIMALS:
            rounding = const.CURRENCY_DECIMALS.get(self.currency_id.name)
        else:
            rounding = self.currency_id.decimal_places
        rounded_amount = float_round(self.amount, rounding, rounding_method='DOWN')
        return {
            'rounded_amount': rounded_amount
        }

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Xendit-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'xendit' or self.payment_method_code == 'card':
            return res

        # Initiate the payment and retrieve the invoice data.
        payload = self._xendit_prepare_invoice_request_payload()
        _logger.info("Sending invoice request for link creation:\n%s", pprint.pformat(payload))
        invoice_data = self.provider_id._xendit_make_request('v2/invoices', payload=payload)
        _logger.info("Received invoice request response:\n%s", pprint.pformat(invoice_data))

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values = {
            'api_url': invoice_data.get('invoice_url')
        }
        return rendering_values

    def _xendit_prepare_invoice_request_payload(self):
        """ Create the payload for the invoice request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        redirect_url = urls.url_join(base_url, '/payment/status')
        payload = {
            'external_id': self.reference,
            'amount': self.amount,
            'description': self.reference,
            'customer': {
                'given_names': self.partner_name,
            },
            'success_redirect_url': redirect_url,
            'failure_redirect_url': redirect_url,
            'payment_methods': [const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code.upper())
            ],
            'currency': self.currency_id.name,
        }
        # Extra payload values that must not be included if empty.
        if self.partner_email:
            payload['customer']['email'] = self.partner_email
        if phone := self.partner_id.mobile or self.partner_id.phone:
            payload['customer']['mobile_number'] = phone
        address_details = {}
        if self.partner_city:
            address_details['city'] = self.partner_city
        if self.partner_country_id.name:
            address_details['country'] = self.partner_country_id.name
        if self.partner_zip:
            address_details['postal_code'] = self.partner_zip
        if self.partner_state_id.name:
            address_details['state'] = self.partner_state_id.name
        if self.partner_address:
            address_details['street_line1'] = self.partner_address
        if address_details:
            payload['customer']['addresses'] = [address_details]

        return payload

    def _send_payment_request(self):
        """ Override of `payment` to send a payment request to Xendit.

        Note: self.ensure_one()

        :return: None
        :raise UserError: If the transaction is not linked to a token.
        """
        super()._send_payment_request()
        if self.provider_code != 'xendit':
            return

        if not self.token_id:
            raise ValidationError("Xendit: " + _("The transaction is not linked to a token."))

        self._xendit_create_charge(self.token_id.provider_ref)

    def _xendit_create_charge(self, token_ref):
        """ Create a charge on Xendit using the `credit_card_charges` endpoint.

        :param str token_ref: The reference of the Xendit token to use to make the payment.
        :return: None
        """
        if self.currency_id.name in const.CURRENCY_DECIMALS:
            rounding = const.CURRENCY_DECIMALS.get(self.currency_id.name)
        else:
            rounding = self.currency_id.decimal_places
        rounded_amount = float_round(self.amount, rounding, rounding_method='DOWN')
        payload = {
            'token_id': token_ref,
            'external_id': self.reference,
            'amount': rounded_amount,
            'currency': self.currency_id.name,
        }
        charge_notification_data = self.provider_id._xendit_make_request(
            'credit_card_charges', payload=payload
        )
        self._handle_notification_data('xendit', charge_notification_data)

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on the notification data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'xendit' or len(tx) == 1:
            return tx

        reference = notification_data.get('external_id')
        if not reference:
            raise ValidationError("Xendit: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'xendit')])
        if not tx:
            raise ValidationError(
                "Xendit: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Xendit data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        self.ensure_one()

        super()._process_notification_data(notification_data)
        if self.provider_code != 'xendit':
            return

        # Update the provider reference.
        self.provider_reference = notification_data.get('id')

        # Update payment method.
        payment_method_code = notification_data.get('payment_method', '')
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = notification_data.get('status')
        if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            if self.tokenize:
                self._xendit_tokenize_from_notification_data(notification_data)
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            failure_reason = notification_data.get('failure_reason')
            self._set_error(_(
                "An error occurred during the processing of your payment (%s). Please try again.",
                failure_reason,
            ))

    def _xendit_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict notification_data: Xendit's response to a charge API request.
        :return: None
        """
        card_info = notification_data['masked_card_number'][-4:]  # Xendit pads details with X's.
        token_id = notification_data['credit_card_token_id']
        token = self.env['payment.token'].create({
            "provider_id": self.provider_id.id,
            "payment_method_id": self.payment_method_id.id,
            "payment_details": card_info,
            "partner_id": self.partner_id.id,
            "provider_ref": token_id,
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
