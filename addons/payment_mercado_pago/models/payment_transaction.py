# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from urllib.parse import quote as url_quote

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.controllers.main import MercadoPagoController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Mercado Pago-specific rendering values.

        Note: self.ensure_one() from `_get_rendering_values`.

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'mercado_pago':
            return res

        # Initiate the payment and retrieve the payment link data.
        payload = self._mercado_pago_prepare_preference_request_payload()
        _logger.info(
            "Sending '/checkout/preferences' request for link creation:\n%s",
            pprint.pformat(payload),
        )
        api_url = self.provider_id._mercado_pago_make_request(
            '/checkout/preferences', payload=payload
        )['init_point' if self.provider_id.state == 'enabled' else 'sandbox_init_point']

        # Extract the payment link URL and params and embed them in the redirect form.
        parsed_url = urls.url_parse(api_url)
        url_params = urls.url_decode(parsed_url.query)
        rendering_values = {
            'api_url': api_url,
            'url_params': url_params,  # Encore the params as inputs to preserve them.
        }
        return rendering_values

    def _mercado_pago_prepare_preference_request_payload(self):
        """ Create the payload for the preference request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        return_url = urls.url_join(base_url, MercadoPagoController._return_url)
        sanitized_reference = url_quote(self.reference)
        webhook_url = urls.url_join(
            base_url, f'{MercadoPagoController._webhook_url}/{sanitized_reference}'
        )  # Append the reference to identify the transaction from the webhook notification data.

        # In the case where we are issuing a preference request in CLP or COP, we must ensure that
        # the price unit is an integer because these currencies do not have a minor unit.
        unit_price = self.amount
        if self.currency_id.name in ('CLP', 'COP'):
            rounded_unit_price = int(self.amount)
            if rounded_unit_price != self.amount:
                raise UserError(_(
                    "Prices in the currency %s must be expressed in integer values.",
                    self.currency_id.name,
                ))
            unit_price = rounded_unit_price

        return {
            'auto_return': 'all',
            'back_urls': {
                'success': return_url,
                'pending': return_url,
                'failure': return_url,
            },
            'external_reference': self.reference,
            'items': [{
                'title': self.reference,
                'quantity': 1,
                'currency_id': self.currency_id.name,
                'unit_price': unit_price,
            }],
            'notification_url': webhook_url,
            'payer': {
                'name': self.partner_name,
                'email': self.partner_email,
                'phone': {
                    'number': self.partner_phone,
                },
                'address': {
                    'zip_code': self.partner_zip,
                    'street_name': self.partner_address,
                },
            },
            'payment_methods': {
                'installments': 1,  # Prevent MP from proposing several installments for a payment.
            },
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Mercado Pago data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'mercado_pago' or len(tx) == 1:
            return tx

        reference = notification_data.get('external_reference')
        if not reference:
            raise ValidationError("Mercado Pago: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'mercado_pago')])
        if not tx:
            raise ValidationError(
                "Mercado Pago: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Mercado Pago data.

        Note: self.ensure_one() from `_process_notification_data`

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'mercado_pago':
            return

        # Update the provider reference.
        payment_id = notification_data.get('payment_id')
        if not payment_id:
            raise ValidationError("Mercado Pago: " + _("Received data with missing payment id."))
        self.provider_reference = payment_id

        # Verify the notification data.
        verified_payment_data = self.provider_id._mercado_pago_make_request(
            f'/v1/payments/{self.provider_reference}', method='GET'
        )

        # Update the payment method.
        payment_method_type = verified_payment_data.get('payment_type_id', '')
        for odoo_code, mp_codes in const.PAYMENT_METHODS_MAPPING.items():
            if any(payment_method_type == mp_code for mp_code in mp_codes.split(',')):
                payment_method_type = odoo_code
                break
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_type, mapping=const.PAYMENT_METHODS_MAPPING
        )
        # Fall back to "unknown" if the payment method is not found (and if "unknown" is found), as
        # the user might have picked a different payment method than on Odoo's payment form.
        if not payment_method:
            payment_method = self.env['payment.method'].search([('code', '=', 'unknown')], limit=1)
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = verified_payment_data.get('status')
        if not payment_status:
            raise ValidationError("Mercado Pago: " + _("Received data with missing status."))

        if payment_status in const.TRANSACTION_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['canceled']:
            self._set_canceled()
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction with reference %s with invalid payment status: %s",
                self.reference, payment_status
            )
            self._set_error(
                "Mercado Pago: " + _("Received data with invalid status: %s", payment_status)
            )
