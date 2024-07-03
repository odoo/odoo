# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import time
import uuid
import requests
import re
import xmlrpc.client


from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.hyperpay import const

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def send_pending(self):
        tx_url = 'http://localhost:8088'
        db = self.env.cr.dbname
        username = 'admin'
        password = 'admin'
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(tx_url), allow_none=True)
        tx_uid = common.authenticate(db, username, password, {})
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(tx_url), allow_none=True)
        tx_ids = models.execute_kw(db, tx_uid, password, 'payment.transaction', 'search', [[['state', '=', 'pending']]])
        for rec in tx_ids:
            self._update_state(rec, 'pending', {'done', 'error', 'cancel'})

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to return hyperpay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'hyperpay':
            return res

        if self.operation in ('online_token', 'offline'):
            return {}

        customer_id = str(self.id)
        eid = self.provider_id.hyperpay_key_id
        order_id = self._hyperpay_create_order(customer_id, eid)['id']
        return {
            'key_id': self.provider_id.hyperpay_key_id,
            'customer_id': customer_id,
            'is_tokenize_request': self.tokenize,
            'order_id': order_id,
        }

    def _hyperpay_create_order(self, customer_id=None, eid=None):
        """ Create and return an Order object to initiate the payment.

        :param str customer_id: The ID of the Customer object to assign to the Order for
                                non-subsequent payments.
        :return: The created Order.
        :rtype: dict
        """
        payload = self._hyperpay_prepare_order_payload(customer_id=customer_id, eid=eid)
        _logger.info(
            "Sending '/payload' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        order_data = self.provider_id._hyperpay_make_request(payload=payload)

        _logger.info(
            "Response of '/orders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(order_data)
        )
        return order_data

    def _hyperpay_prepare_order_payload(self, customer_id=None, eid=None):
        """ Prepare the payload for the order request based on the transaction values.

        :param str customer_id: The ID of the Customer object to assign to the Order for
                                non-subsequent payments.
        :return: The request payload.
        :rtype: dict
        """

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        pm_code = (self.payment_method_id.primary_payment_method_id or self.payment_method_id).code
        payload = {
            'amount': converted_amount,
            'currency': self.currency_id.name,
            'paymentType': 'DB',
            'merchantTransactionId': self.reference,
            'customer.merchantCustomerId': customer_id,
            'entityId': eid
        }

        if self.provider_id.capture_manually:  # The related payment must be only authorized.
            payload.update({
                'payment': {
                    'capture': 'manual',
                    'capture_options': {
                        'manual_expiry_period': 7200,  # The default value for this required option.
                        'refund_speed': 'normal',  # The default value for this required option.
                    }
                },
            })
        return payload

    def _hyperpay_get_mandate_max_amount(self):
        """ Return the eMandate's maximum amount to define.

        :return: The eMandate's maximum amount.
        :rtype: int
        """
        pm_code = (
                self.payment_method_id.primary_payment_method_id or self.payment_method_id
        ).code
        pm_max_amount = const.MANDATE_MAX_AMOUNT.get(pm_code, 100000)
        mandate_values = self._get_mandate_values()  # The linked document's values.
        if 'amount' in mandate_values and 'MRR' in mandate_values:
            max_amount = min(
                pm_max_amount, max(mandate_values['amount'] * 1.5, mandate_values['MRR'] * 5)
            )
        else:
            max_amount = pm_max_amount
        return max_amount

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of `payment` to send a refund request to Hyperpay.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund.
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != 'hyperpay':
            return refund_tx

        # Make the refund request to Hyperpay.
        converted_amount = payment_utils.to_minor_currency_units(
            -refund_tx.amount, refund_tx.currency_id
        )  # The amount is negative for refund transactions.
        payload = {
            'amount': converted_amount,
            'notes': {
                'reference': refund_tx.reference,  # Allow retrieving the ref. from webhook data.
            },
        }
        _logger.info(
            "Payload of '/payments/<id>/refund' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        response_content = refund_tx.provider_id._hyperpay_make_request(
            f'payments/{self.provider_reference}/refund', payload=payload
        )
        _logger.info(
            "Response of '/payments/<id>/refund' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        response_content.update(entity_type='refund')
        refund_tx._handle_notification_data('hyperpay', response_content)

        return refund_tx

    def _send_capture_request(self, amount_to_capture=None):
        """ Override of `payment` to send a capture request to Hyperpay. """
        child_capture_tx = super()._send_capture_request(amount_to_capture=amount_to_capture)
        if self.provider_code != 'hyperpay':
            return child_capture_tx

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        payload = {'amount': converted_amount, 'currency': self.currency_id.name}
        _logger.info(
            "Payload of '/payments/<id>/capture' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        response_content = self.provider_id._hyperpay_make_request(
            f'payments/{self.provider_reference}/capture', payload=payload
        )
        _logger.info(
            "Response of '/payments/<id>/capture' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )

        # Handle the capture request response.
        self._handle_notification_data('hyperpay', response_content)

        return child_capture_tx

    def _handle_notification_data(self, provider_code, notification_data):
        """ Match the transaction with the notification data, update its state and return it.

        :param str provider_code: The code of the provider handling the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction.
        :rtype: recordset of `payment.transaction`
        """
        tx = self._get_tx_from_notification_data(provider_code, notification_data)
        tx._process_notification_data(notification_data)
        tx._execute_callback()
        return tx

    def _send_void_request(self, amount_to_void=None):
        """ Override of `payment` to explain that it is impossible to void a Hyperpay transaction.
        """
        child_void_tx = super()._send_void_request(amount_to_void=amount_to_void)
        if self.provider_code != 'hyperpay':
            return child_void_tx

        raise UserError(_("Transactions processed by Hyperpay can't be manually voided from Odoo."))

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on hyperpay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The normalized notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'hyperpay' or len(tx) == 1:
            return tx

        entity_type = notification_data.get('entity_type', 'payment')
        if entity_type == 'payment':
            reference = notification_data.get('merchantTransactionId')
            if not reference:
                raise ValidationError("Hyperpay: " + _("Received data with missing reference."))
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'hyperpay')])
        else:  # 'refund'
            reference = notification_data.get('notes', {}).get('reference')
            if reference:  # The refund was initiated from Odoo.
                tx = self.search([('reference', '=', reference), ('provider_code', '=', 'hyperpay')])
            else:  # The refund was initiated from Hyperpay.
                # Find the source transaction based on its provider reference.
                source_tx = self.search([
                    ('provider_reference', '=', notification_data['payment_id']),
                    ('provider_code', '=', 'hyperpay'),
                ])
                if source_tx:
                    # Manually create a refund transaction with a new reference.
                    tx = self._hyperpay_create_refund_tx_from_notification_data(
                        source_tx, notification_data
                    )
                else:  # The refund was initiated for an unknown source transaction.
                    pass  # Don't do anything with the refund notification.
        if not tx:
            raise ValidationError(
                "Hyperpay: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _hyperpay_create_refund_tx_from_notification_data(self, source_tx, notification_data):
        """ Create a refund transaction based on Hyperpay data.

        :param recordset source_tx: The source transaction for which a refund is initiated, as a
                                    `payment.transaction` recordset.
        :param dict notification_data: The notification data sent by the provider.
        :return: The newly created refund transaction.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        """
        refund_provider_reference = notification_data.get('id')
        amount_to_refund = notification_data.get('amount')
        if not refund_provider_reference or not amount_to_refund:
            raise ValidationError("Hyperpay: " + _("Received incomplete refund data."))

        converted_amount = payment_utils.to_major_currency_units(
            amount_to_refund, source_tx.currency_id
        )
        return source_tx._create_child_transaction(
            converted_amount, is_refund=True, provider_reference=refund_provider_reference
        )

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Hyperpay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'hyperpay':
            return

        # Update the payment method.
        payment_method = notification_data.get('paymentType')
        if isinstance(payment_method, dict):  # capture/void/refund requests receive a string.
            payment_method_type = payment_method.get('type')
            if self.payment_method_id.code == payment_method_type == 'card':
                payment_method_type = notification_data['payment_method']['card']['brand']
            payment_method = self.env['payment.method']._get_from_code(
                payment_method_type, mapping=const.PAYMENT_METHODS_MAPPING
            )
            self.payment_method_id = payment_method or self.payment_method_id

        # Update the provider reference and the payment state.
        # if self.operation == 'validation':
        #     self.provider_reference = notification_data['setup_intent']['id']
        #     status = notification_data['setup_intent']['status']
        # elif self.operation == 'refund':
        #     self.provider_reference = notification_data['refund']['id']
        #     status = notification_data['refund']['status']
        # else:  # 'online_direct', 'online_token', 'offline'
        #     self.provider_reference = notification_data['payment_intent']['id']
        #     status = notification_data['payment_intent']['status']
        # if not status:
        #     raise ValidationError(
        #         "Stripe: " + _("Received data with missing intent status.")
        #     )

        status_code_url = "https://eu-test.oppwa.com/v1/resultcodes"
        response = requests.get(status_code_url).json()

        status = notification_data['result']['code']
        for elem in response['resultCodes']:
            if status == elem['code']:
                stat_desc = elem['description']

        if re.match(r'^(000.000.|000.100.1|000.[36]|000.400.1[12]0)', status):
            self._set_done()
        elif re.match(r'^(000\.200)', status):
            self._set_pending()
        else:
            _logger.warning(
                "received invalid payment status (%s):%s for transaction with reference %s",
                status, stat_desc, self.reference
            )
            self._set_error(_("Received data with invalid intent status: %s: %s", status, stat_desc))

        # if status in const.STATUS_MAPPING['draft']:
        #     pass
        # elif status in const.STATUS_MAPPING['pending']:
        #     self._set_pending()
        # elif status in const.STATUS_MAPPING['authorized']:
        #     if self.tokenize:
        #         self._stripe_tokenize_from_notification_data(notification_data)
        #     self._set_authorized()
        # elif status in const.STATUS_MAPPING['done']:
        #     if self.tokenize:
        #         self._stripe_tokenize_from_notification_data(notification_data)
        #
        #     self._set_done()
        #
        #     # Immediately post-process the transaction if it is a refund, as the post-processing
        #     # will not be triggered by a customer browsing the transaction from the portal.
        #     if self.operation == 'refund':
        #         self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        # elif status in const.STATUS_MAPPING['cancel']:
        #     self._set_canceled()
        # elif status in const.STATUS_MAPPING['error']:
        #     if self.operation != 'refund':
        #         last_payment_error = notification_data.get('payment_intent', {}).get(
        #             'last_payment_error'
        #         )
        #         if last_payment_error:
        #             message = last_payment_error.get('message', {})
        #         else:
        #             message = _("The customer left the payment page.")
        #         self._set_error(message)
        #     else:
        #         self._set_error(_(
        #             "The refund did not go through. Please log into your Stripe Dashboard to get "
        #             "more information on that matter, and address any accounting discrepancies."
        #         ), extra_allowed_states=('done',))
        # else:  # Classify unknown intent statuses as `error` tx state
        #     _logger.warning(
        #         "received invalid payment status (%s) for transaction with reference %s",
        #         status, self.reference
        #     )
        #     self._set_error(_("Received data with invalid intent status: %s", status))

    def _hyperpay_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict notification_data: The notification data built with Hyperpay objects.
                                       See `_process_notification_data`.
        :return: None
        """
        pm_code = (self.payment_method_id.primary_payment_method_id or self.payment_method_id).code
        if pm_code == 'card':
            details = notification_data.get('card', {}).get('last4')
        elif pm_code == 'upi':
            temp_vpa = notification_data.get('vpa')
            details = temp_vpa[temp_vpa.find('@') - 1:]
        else:
            details = pm_code

        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': details,
            'partner_id': self.partner_id.id,
            # Hyperpay requires both the customer ID and the token ID which are extracted from here.
            'provider_ref': f'{notification_data["customer_id"]},{notification_data["token_id"]}',
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
