# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_worldline import const
from odoo.addons.payment_worldline.controllers.main import WorldlineController


_logger = logging.getLogger(__name__)


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
        res = super()._get_specific_processing_values(processing_values)
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
            res['force_flow'] = 'redirect'
        return res

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Worldline-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'worldline':
            return res

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
        return_url_params = urls.url_encode({'provider_id': str(self.provider_id.id)})
        return_url = f'{urls.url_join(base_url, return_route)}?{return_url_params}'
        payload = {
            'hostedCheckoutSpecificInput': {
                'locale': self.partner_lang,
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
                        'city': self.partner_city,
                        'countryCode': self.partner_country_id.code,
                        'state': self.partner_state_id.name,
                        'street': self.partner_address,
                        'zip': self.partner_zip,
                    },
                    'contactDetails': {
                        'emailAddress': self.partner_email,
                        'phoneNumber': self.partner_phone,
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
                pm_codes = self.env['payment.method'].search([
                    ('active', 'in', [True, False]),
                    ('primary_payment_method_id', '=', self.payment_method_id.id),
                ]).mapped('code')
                worldline_codes = [
                    const.PAYMENT_METHODS_MAPPING[code] for code in pm_codes
                    if code in const.PAYMENT_METHODS_MAPPING
                ]
                payload['hostedCheckoutSpecificInput']['paymentProductFilters'] = {
                    'restrictTo': {
                        'products': worldline_codes,
                    },
                }

        _logger.info(
            "Sending '/hostedcheckouts' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        checkout_session_data = self.provider_id._worldline_make_request(
            'hostedcheckouts', payload=payload
        )
        _logger.info(
            "Response of '/hostedcheckouts' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(checkout_session_data)
        )
        return checkout_session_data

    def _send_payment_request(self):
        """ Override of `payment` to send a payment request to Worldline.

        Note: self.ensure_one()

        :return: None
        :raise UserError: If the transaction is not linked to a token.
        """
        super()._send_payment_request()
        if self.provider_code != 'worldline':
            return

        # Prepare the payment request to Worldline.
        if not self.token_id:
            raise UserError("Worldline: " + _("The transaction is not linked to a token."))

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

        # Make the payment request to Worldline.
        response_content = self.provider_id._worldline_make_request(
            'payments',
            payload=payload,
            idempotency_key=payment_utils.generate_idempotency_key(
                self, scope='payment_request_token'
            )
        )

        # Handle the payment request response.
        _logger.info(
            "Response of /payment request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        self._handle_notification_data('worldline', response_content)

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Worldline data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'worldline' or len(tx) == 1:
            return tx

        payment_output = notification_data.get('payment', {}).get('paymentOutput', {})
        reference = payment_output.get('references', {}).get('merchantReference', '')
        if not reference:
            raise ValidationError(
                "Worldline: " + _("Received data with missing reference %(ref)s.", ref=reference)
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'worldline')])
        if not tx:
            raise ValidationError(
                "Worldline: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment' to process the transaction based on Worldline data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data are received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'worldline':
            return

        # Update the provider reference.
        payment_data = notification_data['payment']
        self.provider_reference = payment_data.get('id', '').rsplit('_', 1)[0]

        # Update the payment method.
        payment_output = payment_data.get('paymentOutput', {})
        if 'cardPaymentMethodSpecificOutput' in payment_output:
            payment_method_data = payment_output['cardPaymentMethodSpecificOutput']
        else:
            payment_method_data = payment_output.get('redirectPaymentMethodSpecificOutput', {})
        payment_method_code = payment_method_data.get('paymentProductId', '')
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status = payment_data.get('status')
        has_token_data = 'token' in payment_method_data
        if not status:
            raise ValidationError("Worldline: " + _("Received data with missing payment state."))

        if status in const.PAYMENT_STATUS_MAPPING['pending']:
            if status == 'AUTHORIZATION_REQUESTED':
                self._set_error("Worldline: " + status)
            elif self.operation == 'validation' \
                 and status in {'PENDING_CAPTURE', 'CAPTURE_REQUESTED'} \
                 and has_token_data:
                    self._worldline_tokenize_from_notification_data(payment_method_data)
                    self._set_done()
            else:
                self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING['done']:
            if self.tokenize and has_token_data:
                self._worldline_tokenize_from_notification_data(payment_method_data)
            self._set_done()
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.info(
                "Received data with invalid payment status (%(status)s) for transaction with"
                " reference %(ref)s",
                {'status': status, 'ref': self.reference},
            )
            self._set_error("Worldline: " + _(
                "Received invalid transaction status %(status)s.", status=status
            ))

    def _worldline_tokenize_from_notification_data(self, pm_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict pm_data: The payment method data sent by the provider
        :return: None
        """
        self.ensure_one()

        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': pm_data.get('card', {}).get('cardNumber', '')[-4:],  # Padded with *
            'partner_id': self.partner_id.id,
            'provider_ref': pm_data['token'],
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "Created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {'token_id': token.id, 'partner_id': self.partner_id.id, 'ref': self.reference},
        )
