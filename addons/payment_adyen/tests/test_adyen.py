# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from werkzeug.exceptions import Forbidden

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils

from .common import AdyenCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon

import logging
from odoo.exceptions import ValidationError
import requests

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

    @mute_logger('odoo.addons.payment_adyen.models.payment_transaction')
    def test_send_refund_request(self):
        self.acquirer.support_refund = 'full_only'  # Should simply not be False
        tx = self.create_transaction(
            'redirect', state='done', acquirer_reference='source_reference'
        )
        tx._reconcile_after_done()  # Create the payment

        # Send the refund request
        with patch(
                'odoo.addons.payment_adyen.models.payment_acquirer.PaymentAcquirer._adyen_make_request',
                new=lambda *args, **kwargs: {'pspReference': "refund_reference", 'status': "received"}
        ):
            tx._send_refund_request()

        refund_tx = self.env['payment.transaction'].search([('source_transaction_id', '=', tx.id)])
        self.assertTrue(
            refund_tx,
            msg="Refunding an Adyen transaction should always create a refund transaction."
        )

        self.assertNotEqual(
            refund_tx.acquirer_reference,
            tx.acquirer_reference,
            msg="The acquirer reference of the refund transaction should different from that of "
                "the source transaction."
        )

    def test_flow_adyen_notification(self):
        """ Simulate an online payment flow with a webhook call and tests the raise of 403 Forbidden errors.

        :return: None
        """

        def call_webhook(received_signature):
            uri = '/payment/adyen/notification'
            url = self._build_url(uri)

            payload = {
                   "notificationItems":[
                      {
                         "NotificationRequestItem":{
                            "additionalData":{
                               "hmacSignature": received_signature
                            },
                            "merchantReference":"Test Transaction",
                            "success":"",
                            "eventCode":""
                         }
                      }
                   ]
                }

            self.create_transaction(flow='redirect')

            #payload = self.create_payload(received_signature)

            response = self._make_json_request(url, payload, prepare_payload=False)

            return response

        self._assert_not_raises(
            Forbidden,
            call_webhook,
            #'gd6ys2pSiL1m0rCDaBskDBJ5JXnfhfGKY9f6OtIwwqo='
            'qs7nSzlw0vu8n6Lic/6a0SNoBKkYPoneLbes2+4jU3M='
        )