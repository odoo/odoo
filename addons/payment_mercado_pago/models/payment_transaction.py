# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import quote as url_quote

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.controllers.main import MercadoPagoController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Mercado Pago-specific rendering values.

        Note: self.ensure_one() from `_get_rendering_values`.

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != 'mercado_pago':
            return super()._get_specific_rendering_values(processing_values)

        # Initiate the payment and retrieve the payment link data.
        payload = self._mercado_pago_prepare_preference_request_payload()
        try:
            response_content = self._send_api_request('POST', '/checkout/preferences', json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        api_url = response_content[
            'init_point' if self.provider_id.state == 'enabled' else 'sandbox_init_point'
        ]

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
        )  # Append the reference to identify the transaction from the webhook payment data.

        unit_price = self.amount
        decimal_places = const.CURRENCY_DECIMALS.get(self.currency_id.name)
        if decimal_places is not None:
            unit_price = float_round(unit_price, decimal_places, rounding_method='DOWN')

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
        }

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'mercado_pago':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('external_reference')

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != 'mercado_pago':
            return super()._extract_amount_data(payment_data)

        amount = payment_data.get('additional_info', {}).get('items', [{}])[0].get(
            'unit_price'
        )
        currency_code = payment_data.get('currency_id')
        return {
            'amount': float(amount),
            'currency_code': currency_code,
            'precision_digits': const.CURRENCY_DECIMALS.get(currency_code),
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'mercado_pago':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        payment_id = payment_data.get('id')
        if not payment_id:
            self._set_error(_("Received data with missing payment id."))
            return
        self.provider_reference = payment_id

        # Update the payment method.
        payment_method_type = payment_data.get('payment_type_id', '')
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
        payment_status = payment_data.get('status')
        if not payment_status:
            self._set_error(_("Received data with missing status."))
            return

        if payment_status in const.TRANSACTION_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['canceled']:
            self._set_canceled()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['error']:
            status_detail = payment_data.get('status_detail')
            _logger.warning(
                "Received data for transaction %s with status %s and error code: %s.",
                self.reference, payment_status, status_detail
            )
            error_message = self._mercado_pago_get_error_msg(status_detail)
            self._set_error(error_message)
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction %s with invalid payment status: %s.",
                self.reference, payment_status
            )
            self._set_error(_("Received data with invalid status: %s.", payment_status))

    @api.model
    def _mercado_pago_get_error_msg(self, status_detail):
        """ Return the error message corresponding to the payment status.

        :param str status_detail: The status details sent by the provider.
        :return: The error message.
        :rtype: str
        """
        return const.ERROR_MESSAGE_MAPPING.get(
            status_detail, const.ERROR_MESSAGE_MAPPING['cc_rejected_other_reason']
        )
