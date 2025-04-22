# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from urllib.parse import urlencode
from hashlib import sha256

import requests

from odoo import _, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import float_round

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_nuvei import const
from odoo.addons.payment_nuvei.controllers.main import NuveiController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Nuvei-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'nuvei':
            return res

        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        if self.payment_method_code in const.FULL_NAME_METHODS and not (first_name and last_name):
            raise UserError(
                "Nuvei: " + _(
                    "%(payment_method)s requires both a first and last name.",
                    payment_method=self.payment_method_id.name,
                )
            )

        # Some payment methods don't support float values, even for currencies that does. Therefore,
        # we must round them.
        is_mandatory_integer_pm = self.payment_method_code in const.INTEGER_METHODS
        rounding = 0 if is_mandatory_integer_pm else self.currency_id.decimal_places
        rounded_amount = float_round(self.amount, rounding, rounding_method='DOWN')

        # Phone numbers need to be standardized and validated.
        phone_number = self.partner_phone and self._phone_format(
            number=self.partner_phone, country=self.partner_country_id, raise_exception=False
        )

        # When a parsing error occurs with Nuvei or the user cancels the order, they do not send the
        # checksum back, as such we need to pass an access token token in the url.
        base_url = self.provider_id.get_base_url()
        return_url = base_url + NuveiController._return_url
        cancel_error_url_params = {
            'tx_ref': self.reference,
            'error_access_token': payment_utils.generate_access_token(self.reference),
        }
        cancel_error_url = f'{return_url}?{urlencode(cancel_error_url_params)}'

        url_params = {
            'address1': self.partner_address or '',
            'city': self.partner_city or '',
            'country': self.partner_country_id.code,
            'currency': self.currency_id.name,
            'email': self.partner_email or '',
            'encoding': 'UTF-8',
            'first_name': first_name,
            'isRebilling': '0',
            'item_amount_1': rounded_amount,
            'item_name_1': self.reference,
            'item_quantity_1': 1,
            'invoice_id': self.reference,
            'last_name': last_name,
            'merchantLocale': self.partner_lang,
            'merchant_id': self.provider_id.nuvei_merchant_identifier,
            'merchant_site_id': self.provider_id.nuvei_site_identifier,
            'payment_method_mode': 'filter',
            'payment_method': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code
            ),
            'phone1': phone_number or '',
            'state': self.partner_state_id.code or '',
            'user_token_id': self.partner_id.id,  # Random string due to some PMs requiring it but not used. USE IT
            'time_stamp': self.create_date.strftime('%Y-%m-%d.%H:%M:%S'),
            'total_amount': rounded_amount,
            'version': '4.0.0',
            'zip': self.partner_zip or '',
            'back_url': cancel_error_url,
            'error_url': cancel_error_url,
            'notify_url': base_url + NuveiController._webhook_url,
            'pending_url': return_url,
            'success_url': return_url,
        }

        checksum = self.provider_id._nuvei_calculate_signature(url_params, incoming=False)
        rendering_values = {
            'api_url': self.provider_id._nuvei_get_api_url(),
            'checksum': checksum,
            'url_params': url_params,
        }
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Nuvei data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'nuvei' or len(tx) == 1:
            return tx

        reference = notification_data.get('invoice_id')
        if not reference:
            raise ValidationError(
                "Nuvei: " + _("Received data with missing reference.")
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'nuvei')])
        if not tx:
            raise ValidationError(
                "Nuvei: " + _("No transaction found matching reference %(ref)s.", ref=reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Nuvei data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data are received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'nuvei':
            return

        if not notification_data:
            self._set_canceled(state_message=_("The customer left the payment page."))
            return

        # Update the provider reference.
        self.provider_reference = notification_data.get('TransactionID')

        # Update the payment method.
        payment_option = notification_data.get('payment_method', '')
        payment_method = self.env['payment.method']._get_from_code(
            payment_option.lower(), mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status = notification_data.get('Status') or notification_data.get('ppp_status')
        if not status:
            raise ValidationError("Nuvei: " + _("Received data with missing payment state."))
        status = status.lower()
        if status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
            token = notification_data.get('tokenId')
            upi = notification_data.get('userPaymentOptionId')
            t_id = notification_data.get('TransactionID')
            self.tokenize(token, upi, t_id)
        elif status in const.PAYMENT_STATUS_MAPPING['error']:
            failure_reason = notification_data.get('Reason') or notification_data.get('message')
            self._set_error(_(
                "An error occurred during the processing of your payment (%(reason)s). Please try"
                " again.", reason=failure_reason,
            ))
        else:  # Classify unsupported payment states as the `error` tx state.
            status_description = notification_data.get('Reason')
            _logger.info(
                "Received data with invalid payment status (%(status)s) and reason '%(reason)s' "
                "for transaction with reference %(ref)s",
                {'status': status, 'reason': status_description, 'ref': self.reference},
            )
            self._set_error("Nuvei: " + _(
                "Received invalid transaction status %(status)s and reason '%(reason)s'.",
                status=status, reason=status_description
            ))

    def tokenize(self, token, upi_id, transaction_id):
        self.ensure_one()

        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': '1234',
            'partner_id': self.partner_id.id,
            'provider_ref': token,
            'nuvei_upi_id': upi_id,
            'ITID': transaction_id,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Adyen.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'nuvei':
            return

        if not self.token_id:
            raise UserError("Nuvei: " + _("The transaction is not linked to a token."))

        time_stamp = self.create_date.strftime('%Y%m%d%H%M%S')
        checksum = self.provider_id.nuvei_merchant_identifier + self.provider_id.nuvei_site_identifier + time_stamp + self.provider_id.nuvei_secret_key
        checksum = sha256(checksum.encode('utf-8')).hexdigest()
        data_token = {
            'merchantId': self.provider_id.nuvei_merchant_identifier,
            'merchantSiteId': self.provider_id.nuvei_site_identifier,
            'timeStamp': time_stamp,
            'checksum': checksum,
        }

        url = 'https://ppp-test.nuvei.com/ppp/api/v1/getSessionToken.do'

        response = requests.post(url, json=data_token, timeout=10)
        sessionToken = response.json()['sessionToken']
        time_stamp2 = self.create_date.strftime('%Y%m%d%H%M%S')
        checksum2 = (
            self.provider_id.nuvei_merchant_identifier
            + self.provider_id.nuvei_site_identifier
            + str(self.amount)
            + self.currency_id.name
            + time_stamp2 +
            self.provider_id.nuvei_secret_key
        )
        checksum2 = sha256(checksum2.encode('utf-8')).hexdigest()
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        data_request = {
            "sessionToken": sessionToken,
            "merchantId": self.provider_id.nuvei_merchant_identifier,
            "merchantSiteId": self.provider_id.nuvei_site_identifier,
            "amount": self.amount,
            "currency": self.currency_id.name,
            "userTokenId": self.token_id.partner_id.id,
            "timeStamp": time_stamp,
            "checksum": checksum2,
            'relatedTransactionId': self.token_id.ITID,
            "paymentOption": {
                "userPaymentOptionId": self.token_id.nuvei_upi_id,
                "card": {
                    "CVV": "123"
                }
            },
            "billingAddress": {
                "country": "US",
                "email": "admin@example.com",
                "firstName": first_name,
                "lastName": last_name,
            },
            "deviceDetails": {
                         "ipAddress": request.httprequest.remote_addr
        },
        }

        url = 'https://ppp-test.nuvei.com/ppp/api/v1/payment.do'

        response = requests.post(url, json=data_request, timeout=10)
