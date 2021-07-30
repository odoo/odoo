# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils

from .common import AdyenCommon

import logging
_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class AdyenForm(AdyenCommon):

    def test_processing_values(self):
        tx = self.create_transaction(flow='direct')
        with mute_logger('odoo.addons.payment.models.payment_transaction'), \
            patch(
                'odoo.addons.payment.utils.generate_access_token',
                new=self._generate_test_access_token
            ):
            processing_values = tx._get_processing_values()

        converted_amount = 111111
        self.assertEqual(
            payment_utils.to_minor_currency_units(self.amount, self.currency),
            converted_amount,
        )
        self.assertEqual(processing_values['converted_amount'], converted_amount)
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            self.assertTrue(payment_utils.check_access_token(
                processing_values['access_token'], self.reference, converted_amount, self.partner.id
            ))

    def test_token_activation(self):
        """Activation of disabled adyen tokens is forbidden"""
        token = self.create_token(active=False)
        with self.assertRaises(UserError):
            token._handle_reactivation_request()

    def test_send_refund_request(self):
        tx = self.create_transaction(flow='dummy', operation='online_redirect',
                                     acquirer_reference='source_reference')
        tx._reconcile_after_done()

        def send_resp_incomplete(self_mock, **kwargs):
            return {}

        self.patch(type(self.env['payment.acquirer']), '_adyen_make_request', send_resp_incomplete)
        with mute_logger('odoo.addons.payment_adyen.models.payment_transaction'), \
             self.assertRaises(ValidationError):
            tx._send_refund_request()

        def send_resp_complete(self_mock, **kwargs):
            return {'pspReference': 'refund_reference', 'response': '[refund-received]'}

        self.patch(type(self.env['payment.acquirer']), '_adyen_make_request', send_resp_complete)
        with mute_logger('odoo.addons.payment_adyen.models.payment_transaction'):
            tx._send_refund_request()
        self.assertEqual(
            tx.refund_transaction_ids[0].acquirer_reference,
            'refund_reference',
            "The refund's acquirer reference should be set with the response."
        )

    def test_refund_notification(self):
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/payment/adyen/notification"
        notification = {
            'live': 'false',
            'notificationItems': [{
                'NotificationRequestItem': {
                    'additionalData': {
                        'hmacSignature': 'Nop'
                    },
                    'amount': {'currency': 'USD', 'value': 100},
                    'eventCode': 'REFUND',
                    'eventDate': '2021-08-02T16:27:23+02:00',
                    'merchantAccountCode': 'merchantCode',
                    'merchantReference': 'TEST',
                    'originalReference': 'original_reference',
                    'pspReference': 'psp_reference',
                    'reason': '',
                    'success': 'true'
                }
            }]
        }
        with mute_logger('odoo.addons.payment_adyen.controllers.main'):
            response = requests.request('POST', url, json=notification, timeout=60).json()['result']
        self.assertEqual(
            response,
            '[accepted]',
            "The notification should be accepted, whatever happened."
        )

    def test_process_feedback_data_with_original_reference(self):
        tx = self.create_transaction(flow='dummy', operation='online_redirect',
                                     acquirer_reference='source_reference')
        refund_tx = tx._create_refund_transaction(refund_amount=11.11,
                                                  acquirer_reference="refund_reference")
        fake_notification = {
            'merchantReference': 'R-Test Transaction',
            'originalReference': 'modified_source_reference',
            'pspReference': 'modified_refund_reference',
            'resultCode': 'Authorised'
        }
        refund_tx._process_feedback_data(fake_notification)
        self.assertEqual(
            tx.acquirer_reference,
            'modified_source_reference',
            "The source acquirer reference should be the one from the notification."
        )
        self.assertEqual(
            refund_tx.acquirer_reference,
            'modified_refund_reference',
            "The refund's acquirer reference should be the one from the notification."
        )
