# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_flutterwave import const
from odoo.addons.payment_flutterwave.controllers.main import FlutterwaveController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to redirect pending token-flow transactions.

        If the financial institution insists on 3-D Secure authentication, this
        override will redirect the user to the provided authorization page.

        Note: `self.ensure_one()`
        """
        if not self._flutterwave_is_authorization_pending():
            return super()._get_specific_processing_values(processing_values)

        return {'redirect_form_html': self.env['ir.qweb']._render(
            self.provider_id.redirect_form_view_id.id,
            {'auth_url': self.provider_reference},
        )}

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
            'redirect_url': urls.urljoin(base_url, FlutterwaveController._return_url),
            'customer': {
                'email': self.partner_email,
                'name': self.partner_name,
                'phonenumber': self.partner_phone,
            },
            'customizations': {
                'title': self.company_id.name,
                'logo': urls.urljoin(base_url, f'web/image/res.company/{self.company_id.id}/logo'),
            },
            'payment_options': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code
            ),
        }
        try:
            payment_link_data = self._send_api_request('POST', 'payments', json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        # Extract the payment link URL and embed it in the redirect form.
        return {'api_url': payment_link_data['link']}

    def _send_payment_request(self):
        """Override of `payment` to send a payment request to Flutterwave."""
        if self.provider_code != 'flutterwave':
            return super()._send_payment_request()

        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        base_url = self.provider_id.get_base_url()
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
            'redirect_url': urls.urljoin(base_url, FlutterwaveController._auth_return_url),
        }

        try:
            response_content = self._send_api_request('POST', 'tokenized-charges', json=data)
        except ValidationError as error:
            self._set_error(str(error))
        else:
            self._process('flutterwave', response_content)

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'flutterwave':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('tx_ref') or payment_data.get('txRef')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'flutterwave':
            return super()._extract_amount_data(payment_data)

        amount = payment_data.get('amount')
        currency_code = payment_data.get('currency')
        return {
            'amount': float(amount),
            'currency_code': currency_code,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'flutterwave':
            return super()._apply_updates(payment_data)

        # Update the provider reference.
        self.provider_reference = payment_data['id']

        # Update payment method.
        payment_method_type = payment_data.get('payment_type', '')
        if payment_method_type == 'card':
            payment_method_type = payment_data.get('card', {}).get('type').lower()
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_type, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = payment_data['status'].lower()
        if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            auth_url = payment_data.get('meta', {}).get('authorization', {}).get('redirect')
            if auth_url:
                # will be set back to the actual value after moving away from pending
                self.provider_reference = auth_url
            self._set_pending()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "An error occurred during the processing of your payment (status %s). Please try "
                "again.", payment_status
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction %s.",
                payment_status, self.reference
            )
            self._set_error(_("Unknown payment status: %s", payment_status))

    def _extract_token_values(self, payment_data):
        """Override of `payment` to extract the token values from the payment data."""
        if self.provider_code != 'flutterwave':
            return super()._extract_token_values(payment_data)

        if 'token' not in payment_data.get('card', {}):
            return {}

        return {
            'payment_details': payment_data['card']['last_4digits'],
            'provider_ref': payment_data['card']['token'],
            'flutterwave_customer_email': payment_data['customer']['email'],
        }

    def _flutterwave_is_authorization_pending(self):
        """ Filter Flutterwave token transactions that are awaiting external authorization.

        :return: Pending transactions awaiting authorization.
        :rtype: recordset of `payment.transaction`
        """
        return self.filtered_domain([
            ('provider_code', '=', 'flutterwave'),
            ('operation', '=', 'online_token'),
            ('state', '=', 'pending'),
            ('provider_reference', 'ilike', 'https'),
        ])
