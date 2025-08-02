# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_worldline import const
from odoo.addons.payment_worldline.controllers.main import WorldlineController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of `payment` to ensure that Worldline requirement for references is satisfied.

        Worldline requires for references to be at most 30 characters long.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        reference = super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )
        if provider_code != 'worldline':
            return reference

        if len(reference) <= 30:  # Worldline transaction merchantReference is limited to 30 chars
            return reference

        prefix = payment_utils.singularize_reference_prefix(prefix='WL')
        return super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to redirect failed token-flow transactions.

        If the financial institution insists on user authentication,
        this override will reset the transaction, and switch the flow to redirect.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        if (
            self.provider_code == 'worldline'
            and self.operation == 'online_token'
            and self.state == 'error'
            and self.state_message.endswith('AUTHORIZATION_REQUESTED')
        ):
            # Tokenized payment failed due to 3-D Secure authentication request.
            # Reset transaction to draft and switch to redirect flow.
            self.write({
                'state': 'draft',
                'operation': 'online_redirect',
            })
            return {'force_flow': 'redirect'}
        return super()._get_specific_processing_values(processing_values)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Worldline-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != 'worldline':
            return super()._get_specific_rendering_values(processing_values)

        checkout_session_data = self._worldline_create_checkout_session()
        return {'api_url': checkout_session_data['redirectUrl']}

    def _worldline_create_checkout_session(self):
        """ Create a hosted checkout session and return the response data.

        :return: The hosted checkout session data.
        :rtype: dict
        """
        self.ensure_one()

        base_url = self.provider_id.get_base_url()
        return_route = WorldlineController._return_url
        return_url_params = url_encode({'provider_id': str(self.provider_id.id)})
        return_url = f'{urls.urljoin(base_url, return_route)}?{return_url_params}'
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        payload = {
            'hostedCheckoutSpecificInput': {
                'locale': self.partner_lang or '',
                'returnUrl': return_url,
                'showResultPage': False,
            },
            'order': {
                'amountOfMoney': {
                    'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
                    'currencyCode': self.currency_id.name,
                },
                'customer': {  # required to create a token and for some redirected payment methods
                    'billingAddress': {
                        'city': self.partner_city or '',
                        'countryCode': self.partner_country_id.code or '',
                        'state': self.partner_state_id.name or '',
                        'street': self.partner_address or '',
                        'zip': self.partner_zip or '',
                    },
                    'contactDetails': {
                        'emailAddress': self.partner_email or '',
                        'phoneNumber': self.partner_phone or '',
                    },
                    'personalInformation': {
                        'name': {
                            'firstName': first_name or '',
                            'surname': last_name or '',
                        },
                    },
                },
                'references': {
                    'descriptor': self.reference,
                    'merchantReference': self.reference,
                },
            },
        }
        if self.payment_method_id.code in const.REDIRECT_PAYMENT_METHODS:
            payload['redirectPaymentMethodSpecificInput'] = {
                'requiresApproval': False,  # Force the capture.
                'paymentProductId': const.PAYMENT_METHODS_MAPPING[self.payment_method_id.code],
                'redirectionData': {
                    'returnUrl': return_url,
                },
            }
        else:
            payload['cardPaymentMethodSpecificInput'] = {
                'authorizationMode': 'SALE',  # Force the capture.
                'tokenize': self.tokenize,
            }
            if not self.payment_method_id.brand_ids and self.payment_method_id.code != 'card':
                worldline_code = const.PAYMENT_METHODS_MAPPING.get(self.payment_method_id.code, 0)
                payload['cardPaymentMethodSpecificInput']['paymentProductId'] = worldline_code
            else:
                payload['hostedCheckoutSpecificInput']['paymentProductFilters'] = {
                    'restrictTo': {
                        'groups': ['cards'],
                    },
                }

        checkout_session_data = self._send_api_request('POST', 'hostedcheckouts', json=payload)

        return checkout_session_data

    def _send_payment_request(self):
        """Override of `payment` to send a payment request to Worldline."""
        if self.provider_code != 'worldline':
            return super()._send_payment_request()

        # Prepare the payment request to Worldline.
        payload = {
            'cardPaymentMethodSpecificInput': {
                'authorizationMode': 'SALE',  # Force the capture.
                'token': self.token_id.provider_ref,
                'unscheduledCardOnFileRequestor': 'merchantInitiated',
                'unscheduledCardOnFileSequenceIndicator': 'subsequent',
            },
            'order': {
                'amountOfMoney': {
                    'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
                    'currencyCode': self.currency_id.name,
                },
                'references': {
                    'merchantReference': self.reference,
                },
            },
        }

        try:
            # Send the payment request to Worldline.
            response_content = self._send_api_request(
                'POST',
                'payments',
                json=payload,
                idempotency_key=payment_utils.generate_idempotency_key(
                    self, scope='payment_request_token'
                )
            )
        except ValidationError as e:
            self._set_error(str(e))
        else:
            self._process('worldline', response_content)

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'worldline':
            return super()._extract_reference(provider_code, payment_data)

        # In case of failed payment, paymentResult could be given as a separate key
        payment_result = payment_data.get('paymentResult', payment_data)
        payment_output = payment_result.get('payment', {}).get('paymentOutput', {})
        return payment_output.get('references', {}).get('merchantReference', '')

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != 'worldline':
            return super()._extract_amount_data(payment_data)

        # In case of failed payment, paymentResult could be given as a separate key
        payment_result = payment_data.get('paymentResult', payment_data)
        amount_of_money = payment_result.get('payment', {}).get('paymentOutput', {}).get(
            'amountOfMoney', {}
        )
        amount = payment_utils.to_major_currency_units(
            amount_of_money.get('amount', 0), self.currency_id
        )
        currency_code = amount_of_money.get('currencyCode')
        return {
            'amount': amount,
            'currency_code': currency_code,
        }

    def _apply_updates(self, payment_data):
        """ Override of `payment' to process the transaction based on Worldline data.

        Note: self.ensure_one()

        :param dict payment_data: The payment data sent by the provider.
        :return: None
        """
        if self.provider_code != 'worldline':
            return super()._apply_updates(payment_data)

        # In case of failed payment, paymentResult could be given as a separate key
        payment_result = payment_data.get('paymentResult', payment_data)
        payment_data = payment_result.get('payment', {})

        # Update the provider reference.
        self.provider_reference = payment_data.get('id', '').rsplit('_', 1)[0]

        # Update the payment method.
        payment_method_data = self._worldline_extract_payment_method_data(payment_data)
        payment_method_code = payment_method_data.get('paymentProductId', '')
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status = payment_data.get('status')
        has_token_data = 'token' in payment_method_data
        if not status:
            self._set_error(_("Received data with missing payment state."))
        elif status in const.PAYMENT_STATUS_MAPPING['pending']:
            if status == 'AUTHORIZATION_REQUESTED':
                self._set_error(status)
            elif self.operation == 'validation' \
                 and status in {'PENDING_CAPTURE', 'CAPTURE_REQUESTED'} \
                 and has_token_data:
                    self._set_done()
            else:
                self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        else:
            error_code = None
            if errors := payment_data.get('statusOutput', {}).get('errors'):
                error_code = errors[0].get('errorCode')
            if status in const.PAYMENT_STATUS_MAPPING['cancel']:
                self._set_canceled(_(
                    "Transaction cancelled with error code %(error_code)s.",
                    error_code=error_code,
                ))
            elif status in const.PAYMENT_STATUS_MAPPING['declined']:
                self._set_error(_(
                    "Transaction declined with error code %(error_code)s.",
                    error_code=error_code,
                ))
            else:  # Classify unsupported payment status as the `error` tx state.
                _logger.info(
                    "Received data with invalid payment status (%(status)s) for transaction with "
                    "reference %(ref)s.",
                    {'status': status, 'ref': self.reference},
                )
                self._set_error(_(
                    "Received invalid transaction status %(status)s with error code "
                    "%(error_code)s.",
                    status=status,
                    error_code=error_code,
                ))

    @staticmethod
    def _worldline_extract_payment_method_data(payment_data):
        payment_output = payment_data.get('paymentOutput', {})
        if 'cardPaymentMethodSpecificOutput' in payment_output:
            payment_method_data = payment_output['cardPaymentMethodSpecificOutput']
        else:
            payment_method_data = payment_output.get('redirectPaymentMethodSpecificOutput', {})
        return payment_method_data

    def _extract_token_values(self, payment_data):
        """Override of `payment` to return token data based on Worldline data.

        Note: self.ensure_one() from :meth: `_tokenize`

        :param dict payment_data: The payment data sent by the provider.
        :return: Data to create a token.
        :rtype: dict
        """
        if self.provider_code != 'worldline':
            return super()._extract_token_values(payment_data)

        payment_data = payment_data.get('payment', {})
        payment_method_data = self._worldline_extract_payment_method_data(payment_data)
        if 'token' not in payment_method_data:
            return {}

        # Padded with *
        payment_details = payment_method_data.get('card', {}).get('cardNumber', '')[-4:]
        return {
            'payment_details': payment_details,
            'provider_ref': payment_method_data['token'],
        }
