# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode
from uuid import uuid4

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import float_round

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_nuvei import const
from odoo.addons.payment_nuvei.controllers.main import NuveiController


_logger = get_payment_logger(__name__)


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
        if self.provider_code != 'nuvei':
            return super()._get_specific_rendering_values(processing_values)

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
            'first_name': first_name[:30],
            'item_amount_1': rounded_amount,
            'item_name_1': self.reference,
            'item_quantity_1': 1,
            'invoice_id': self.reference,
            'last_name': last_name[:40],
            'merchantLocale': self.partner_lang,
            'merchant_id': self.provider_id.nuvei_merchant_identifier,
            'merchant_site_id': self.provider_id.nuvei_site_identifier,
            'payment_method_mode': 'filter',
            'payment_method': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code
            ),
            'phone1': phone_number or '',
            'state': self.partner_state_id.code or '',
            'user_token_id': uuid4(),  # Random string due to some PMs requiring it but not used.
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

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'nuvei':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('invoice_id')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'nuvei':
            return super()._extract_amount_data(payment_data)

        # When a user declines to pay and leaves the payment page, no information
        # is sent back to odoo via the endpoint. As such there is no currency or
        # amount set so we return early. This only occurs in the leaving flow so
        # no issue should arise leaving early.
        if not payment_data:
            return

        is_mandatory_integer_pm = self.payment_method_code in const.INTEGER_METHODS
        rounding = 0 if is_mandatory_integer_pm else self.currency_id.decimal_places

        amount = payment_data.get('totalAmount')
        currency_code = payment_data.get('currency')
        return {
            'amount': float(amount),
            'currency_code': currency_code,
            'precision_digits': rounding,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'nuvei':
            return super()._apply_updates(payment_data)

        if not payment_data:
            self._set_canceled(state_message=_("The customer left the payment page."))
            return

        # Update the provider reference.
        self.provider_reference = payment_data.get('TransactionID')

        # Update the payment method.
        payment_option = payment_data.get('payment_method', '')
        payment_method = self.env['payment.method']._get_from_code(
            payment_option, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status = payment_data.get('Status') or payment_data.get('ppp_status')
        if not status:
            self._set_error(_("Received data with missing payment state."))
            return
        status = status.lower()
        if status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING['error']:
            failure_reason = payment_data.get('Reason') or payment_data.get('message')
            self._set_error(_(
                "An error occurred during the processing of your payment (%(reason)s). Please try"
                " again.", reason=failure_reason,
            ))
        else:  # Classify unsupported payment states as the `error` tx state.
            status_description = payment_data.get('Reason')
            _logger.info(
                "Received data with invalid payment status (%(status)s) and reason '%(reason)s' "
                "for transaction %(ref)s.",
                {'status': status, 'reason': status_description, 'ref': self.reference},
            )
            self._set_error(_(
                "Received invalid transaction status %(status)s and reason '%(reason)s'.",
                status=status, reason=status_description
            ))
