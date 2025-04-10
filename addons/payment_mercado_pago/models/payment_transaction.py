# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from urllib.parse import quote as url_quote

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_mercado_pago import const
from odoo.addons.payment_mercado_pago.controllers.main import MercadoPagoController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

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

    def _compare_notification_data(self, notification_data):
        """ Override of `payment` to compare the transaction based on Mercado Pago data.

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If the transaction's amount and currency don't match the
            notification data.
        """
        if self.provider_code != 'mercado_pago':
            return super()._compare_notification_data(notification_data)

        amount = notification_data.get('additional_info', {}).get('items', [{}])[0].get(
            'unit_price'
        )
        # The currency code isn't included in the notification data, so we can't validate it.
        self._validate_amount_and_currency(
            amount,
            self.currency_id.name,
            precision_digits=const.CURRENCY_DECIMALS.get(self.currency_id.name),
        )

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
        payment_id = notification_data.get('id')
        if not payment_id:
            raise ValidationError("Mercado Pago: " + _("Received data with missing payment id."))
        self.provider_reference = payment_id

        # Update the payment method.
        payment_method_type = notification_data.get('payment_type_id', '')
        for odoo_code, mp_codes in const.PAYMENT_METHODS_MAPPING.items():
            if any(payment_method_type == mp_code for mp_code in mp_codes.split(',')):
                payment_method_type = odoo_code
                break
        if payment_method_type == 'card':
            payment_method_code = notification_data.get('payment_method_id')
        else:
            payment_method_code = payment_method_type
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        # Fall back to "unknown" if the payment method is not found (and if "unknown" is found), as
        # the user might have picked a different payment method than on Odoo's payment form.
        if not payment_method:
            payment_method = self.env['payment.method'].search([('code', '=', 'unknown')], limit=1)
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = notification_data.get('status')
        if not payment_status:
            raise ValidationError("Mercado Pago: " + _("Received data with missing status."))

        if payment_status in const.TRANSACTION_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['done']:
            self._set_done()
            if self.tokenize:
                self._mercado_pago_tokenize_from_notification_data({'email': notification_data['payer']['email'], 'token': notification_data.get('token'), 'issuer_id': notification_data.get('issuer_id'), 'payment_method_id': notification_data.get('payment_method_id')})
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['canceled']:
            self._set_canceled()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING['error']:
            status_detail = notification_data.get('status_detail')
            _logger.warning(
                "Received data for transaction with reference %s with status %s and error code: %s",
                self.reference, payment_status, status_detail
            )
            error_message = self._mercado_pago_get_error_msg(status_detail)
            self._set_error(error_message)
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction with reference %s with invalid payment status: %s",
                self.reference, payment_status
            )
            self._set_error(
                "Mercado Pago: " + _("Received data with invalid status: %s", payment_status)
            )

    @api.model
    def _mercado_pago_get_error_msg(self, status_detail):
        """ Return the error message corresponding to the payment status.

        :param str status_detail: The status details sent by the provider.
        :return: The error message.
        :rtype: str
        """
        return "Mercado Pago: " + const.ERROR_MESSAGE_MAPPING.get(
            status_detail, const.ERROR_MESSAGE_MAPPING['cc_rejected_other_reason']
        )

    def _mercado_pago_tokenize_from_notification_data(self, notification_data):

        response = self.provider_id._mercado_pago_make_request(
            f'/v1/customers/search', method='GET', payload=notification_data['email']
        )
        if not response['results']:
            response = self.provider_id._mercado_pago_make_request(
                f'/v1/customers', method='POST', payload=notification_data['email']
            )
            customer_id = response['id']
        else:
            customer_id = response['results'][0]['id']
        #assosiate card with customer
        payload = {
            "token": notification_data['token'],
            "issuer_id": int(notification_data['issuer_id']),
            "payment_method_id": notification_data['payment_method_id']
        }
        response = self.provider_id._mercado_pago_make_request(f'/v1/customers/{customer_id}/cards', method='POST', payload=payload)
        card_id = response['id']
        last_four_digits = response.get('last_four_digits')
        #generate a card token
        response = self.provider_id._mercado_pago_make_request(f'/v1/card_tokens', method='POST', payload={'card_id': card_id})

        data = {
            'transaction_amount': 100,
            'token': response['id'],
            'installments': 1,
            'payer': {
                'type': 'customer',
                'id': customer_id,
            }
        }

        # WHERE THE FUCK IS SECURITY CODE COMING FROM?!
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': last_four_digits,
            'partner_id': self.partner_id.id,
            'provider_ref': response['id'],
            'mercado_pago_customer_id': customer_id,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "Created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )
        return

    def _send_payment_request(self):
        super()._send_payment_request()
        if self.provider_code != 'mercado_pago':
            return

        if not self.token_id:
            raise UserError("Mercado Pago: " + _("The transaction is not linked to a token."))

        data = {
            'transaction_amount': 100,
            'token': self.token_id.provider_ref,
            'installments': 1,
            'payer': {
                'type': 'customer',
                'id': self.token_id.mercado_pago_customer_id,
            },
            'payment_method_id': 'master',
            "point_of_interaction": {
                "type": "SUBSCRIPTIONS",
                "transaction_data": {
                    "first_time_use": False,
                    "subscription_id": "COLLECTORPADRE-SUBSCRIPCION_ID",
                    "payment_reference": {
                        "id": "1334388021"
                    }
                },

            }
        }

        response_content = self.provider_id._mercado_pago_make_request(
            endpoint=f'/v1/payments',
            payload=data,
            method='POST',
            idempotency_key=payment_utils.generate_idempotency_key(
                self
            )
        )

        self._handle_notification_data('mercado_pago', response_content)
