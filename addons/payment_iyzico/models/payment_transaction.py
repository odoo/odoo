# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_iyzico import const


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # === BUSINESS METHODS - PRE-PROCESSING === #

    def _get_specific_rendering_values(self, *args):
        """Override of `payment` to return Iyzico specific rendering values.

         Note: `self.ensure_one()` from :meth:`_get_processing_values`

        :return: The provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != 'iyzico':
            return super()._get_specific_rendering_values(*args)

        # Initiate the payment and retrieve the payment link data.
        payload = self._iyzico_prepare_cf_initialize_payload()
        try:
            payment_link_data = self._send_api_request(
                'POST',
                'payment/iyzipos/checkoutform/initialize/auth/ecom',
                json=payload,
            )
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        # Extract the payment link URL and params and embed them in the redirect form.
        api_url = payment_link_data['paymentPageUrl']
        parsed_url = urls.url_parse(api_url)
        url_params = urls.url_decode(parsed_url.query)

        return {
            'api_url': api_url,
            'url_params': url_params,  # Encore the params as inputs to preserve them.
        }

    def _iyzico_prepare_cf_initialize_payload(self):
        """Create the payload for the CF-initialize request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        query_string_params = urls.url_encode({'tx_ref': self.reference})
        return_url = f'{urljoin(base_url, const.PAYMENT_RETURN_ROUTE)}?{query_string_params}'
        return {
            # Dummy basket item as it is required in Iyzico.
            'basketItems': [{
                'id': self.id,
                'price': self.amount,
                'name': 'Odoo purchase',
                'category1': 'Service',
                'itemType': 'VIRTUAL',
            }],
            'billingAddress': {
                'address': self.partner_address,
                'contactName': self.partner_name,
                'city': self.partner_city,
                'country': self.partner_country_id.name,
            },
            'buyer': {
                'id': self.partner_id.id,
                'name': first_name,
                'surname': last_name,
                'identityNumber': str(self.partner_id.id).zfill(5),
                'email': self.partner_email,
                'registrationAddress': self.partner_address,
                'city': self.partner_city,
                'country': self.partner_country_id.name,
                'ip': '0',
            },
            'callbackUrl': return_url,
            'conversationId': self.reference,
            'currency': self.currency_id.name,
            'locale': 'tr' if self.env.lang == 'tr_TR' else 'en',
            'paidPrice': self.amount,
            'paymentSource': 'ODOO',
            'price': self.amount,
        }

    # === BUSINESS METHODS - PROCESSING === #

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'iyzico':
            return super()._extract_amount_data(payment_data)

        return {
            'amount': payment_data.get('price'),
            'currency_code': payment_data.get('currency'),
        }

    def _apply_updates(self, payment_data):
        """Override of payment to update the transaction based on the payment data."""
        if self.provider_code != 'iyzico':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        self.provider_reference = payment_data.get('paymentId')

        # Update the payment method.
        if bool(payment_data.get('cardType')):
            payment_method_code = payment_data.get('cardAssociation', '')
            payment_method = self.env['payment.method']._get_from_code(
                payment_method_code.lower(), mapping=const.PAYMENT_METHODS_MAPPING
            )
        elif bool(payment_data.get('bankName')):
            payment_method = self.env.ref('payment.payment_method_bank_transfer')
        else:
            payment_method = self.env.ref('payment.payment_method_unknown')
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status = payment_data.get('paymentStatus')
        if status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(self.env._(
                "An error occurred during processing of your payment (code %(code)s:"
                " %(explanation)s). Please try again.",
                code=status, explanation=payment_data.get('errorMessage'),
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction with reference %s",
                status, self.reference
            )
            self._set_error(self.env._("Unknown status code: %s", status))
