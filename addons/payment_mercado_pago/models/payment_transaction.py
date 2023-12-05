# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, models, api
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_mercado_pago.const import TRANSACTION_STATUS_MAPPING
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

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values = {
            'api_url': api_url,
        }
        return rendering_values

    def _mercado_pago_prepare_preference_request_payload(self):
        """ Create the payload for the preference request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        return_url = urls.url_join(base_url, MercadoPagoController._return_url)
        webhook_url = urls.url_join(
            base_url, f'{MercadoPagoController._webhook_url}/{self.reference}'
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

        payment_id = notification_data.get('payment_id')
        if not payment_id:
            raise ValidationError("Mercado Pago: " + _("Received data with missing payment id."))
        self.provider_reference = payment_id

        # Verify the notification data.
        verified_payment_data = self.provider_id._mercado_pago_make_request(
            f'/v1/payments/{self.provider_reference}', method='GET'
        )

        payment_status = verified_payment_data.get('status')
        if not payment_status:
            raise ValidationError("Mercado Pago: " + _("Received data with missing status."))

        if payment_status in TRANSACTION_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in TRANSACTION_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in TRANSACTION_STATUS_MAPPING['canceled']:
            self._set_canceled()
        elif payment_status in TRANSACTION_STATUS_MAPPING['error']:
            state_message = self._mercado_pago_response_msg(verified_payment_data)
            status_detail = verified_payment_data.get('status_detail')
            _logger.warning(
                "Received data for transaction with reference %s with status: %s and error code: %s",
                self.reference, payment_status, status_detail
            )
            self._set_error(state_message)
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction with reference %s with invalid payment status: %s",
                self.reference, payment_status
            )
            self._set_error(
                "Mercado Pago: " + _("Received data with invalid status: %s", payment_status)
            )

    @api.model
    def _mercado_pago_response_msg(self, verified_payment_data):
        """ Return the response status in the human language.

        :return: The response message
        :param dict verified_payment_data: MercadoPago transaction response
        """
        mercadopago_messages = {
            'accredited': _("Mercado Pago: Your payment has been credited. In your summary you will see the charge of {amount} as {statement_descriptor}."),
            'pending_contingency': _("Mercado Pago: We are processing your payment. Don't worry, less than 2 business days we will notify you by e-mail if your payment has been credited."),
            'pending_review_manual': _("Mercado Pago: We are processing your payment. Don't worry, less than 2 business days we will notify you by e-mail if your payment has been credited or if we need more information."),
            'cc_rejected_bad_filled_card_number': _("Mercado Pago: Check the card number."),
            'cc_rejected_bad_filled_date': _("Mercado Pago: Check expiration date."),
            'cc_rejected_bad_filled_other': _("Mercado Pago: Check the data."),
            'cc_rejected_bad_filled_security_code': _("Mercado Pago: Check the card security code."),
            'cc_rejected_blacklist': _("Mercado Pago: We were unable to process your payment, please use another card."),
            'cc_rejected_call_for_authorize': _("Mercado Pago: You must authorize before {payment_method_id} the payment of {amount}."),
            'cc_rejected_card_disabled': _("Mercado Pago: Call {payment_method_id} to activate your card or use another payment method. The phone number is on the back of your card."),
            'cc_rejected_card_error': _("Mercado Pago: We were unable to process your payment, please check your card information."),
            'cc_rejected_duplicated_payment': _("Mercado Pago: If you need to pay again, use another card or another payment method."),
            'cc_rejected_high_risk': _("Mercado Pago: We were unable to process your payment, please use another car."),
            'cc_rejected_insufficient_amount': _("Mercado Pago: Your {payment_method_id} has not enough funds."),
            'cc_rejected_invalid_installments': _("Mercado Pago: {payment_method_id} does not process payments in {installments} installments."),
            'cc_rejected_max_attempts': _("Mercado Pago: You have reached the limit of allowed attempts. Choose another card or other means of payment."),
            'cc_rejected_other_reason': _("Mercado Pago: {payment_method_id} did not process payment, use another card or contact issuer.")
        }
        status = verified_payment_data.get('status_detail', 'cc_rejected_other_reason')
        try:
            message = mercadopago_messages[status].format(
                payment_method_id=verified_payment_data.get('payment_method_id'),
                amount=verified_payment_data.get('transaction_amount'),
                statement_descriptor=verified_payment_data.get('statement_descriptor'),
                installments=verified_payment_data.get('installments')
            )
        except KeyError:
            message = _("Mercadopago could not process this payment. Error code: %s") % verified_payment_data.get('status_detail')
        return message
