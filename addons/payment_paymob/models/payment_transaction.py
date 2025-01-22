# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paymob import const
from odoo.addons.payment_paymob.controllers.main import PaymobController
from odoo.tools.safe_eval import expr_eval, safe_eval


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    paymob_client_secret = fields.Char()

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of `payment` to ensure that Paymob references are unique.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code == 'paymob':
            prefix = payment_utils.singularize_reference_prefix()

        return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Paymob-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific rendering values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'paymob':
            return res

        if not self.paymob_client_secret:
            payload = self._paymob_prepare_payment_request_payload()
            _logger.info("sending '/v1/intention/' request for link creation:\n%s",
                         pprint.pformat(payload))
            payment_data = self.provider_id._paymob_make_request('/v1/intention/', data=payload)

            # The provider reference is set now to allow fetching the payment status after redirection
            self.provider_reference = payment_data.get('id')
            self.paymob_client_secret = payment_data.get('client_secret')

        paymob_url = self.provider_id._paymob_get_api_url()
        api_url = f'''{paymob_url}/unifiedcheckout/?publicKey={
            payment_utils.get_normalized_field(self.provider_id.paymob_public_key)
            }&clientSecret={self.paymob_client_secret}'''

        parsed_url = urls.url_parse(api_url)
        url_params = urls.url_decode(parsed_url.query)
        return {'api_url': api_url, 'url_params': url_params}

    def _paymob_prepare_payment_request_payload(self):
        """ Create the payload for the payment request based on the transaction values.

        :return: The request payload
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        # base_url = "https://8103-178-51-240-182.ngrok-free.app"
        public_key = self.provider_id.paymob_public_key
        redirect_url = urls.url_join(base_url, PaymobController._return_url)
        webhook_url = urls.url_join(base_url, PaymobController._webhook_url)
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)

        return {
            'special_reference': self.reference,
            'amount': self.amount * const.CURRENCY_DECIMAL_MAPPING[self.currency_id.name],
            'currency': self.currency_id.name,
            # 'payment_methods': self.provider_id.paymob_integration_ids.mapped(
            #     lambda pi_id: int(pi_id.name)),
            'payment_methods': self.provider_id.payment_method_ids.mapped('code'),
            'notification_url': webhook_url,
            'redirection_url': redirect_url,
            'billing_data': {
                'first_name': partner_first_name,
                'last_name': partner_last_name,
                'email': self.partner_email,
                'street': self.partner_address,
                'state': self.partner_state_id.name,
                'phone_number': self.partner_phone,
                'country': self.partner_country_id.code,
            },
            'customer': {
                'first_name': partner_first_name,
                'last_name': partner_last_name,
                'email': self.partner_email,
            },
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Paymob data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'paymob' or len(tx) == 1:
            return tx

        tx = self.search([('reference', '=', notification_data.get(
            'merchant_order_id')), ('provider_code', '=', 'paymob')])
        if not tx:
            raise ValidationError("Paymob: " + _(
                "No transaction found matching reference %s.", notification_data.get('ref')
            ))
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Paymob data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'paymob':
            return

        # Update the payment method.
        payment_method_type = notification_data.get('source_data.type', '')
        payment_method = self.env['payment.method']._get_from_code(payment_method_type)
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        if notification_data.get('pending') == 'true':
            self._set_pending()
        elif notification_data.get('success') == 'true':
            self._set_done()
        elif notification_data.get('is_voided') == 'true':
            self._set_canceled("Paymob: " + _("Cancelled payment: 'is_voided' was set to true"))
        elif notification_data.get('success') == 'false':
            _logger.info(
                "Received data with unsuccessful payment status for transaction with reference %s",
                self.reference
            )
            message = notification_data.get('data.message')
            self._set_error(_(
                "Paymob: " +
                "An error occurred during the processing of your payment (%s). Please try again.",
                message,
            ))
