# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_adyen.controllers.main import AdyenController
from odoo.addons.payment_adyen.tests.common import AdyenCommon


@tagged('post_install', '-at_install')
class AdyenTest(AdyenCommon, PaymentHttpCommon):

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

    @mute_logger('odoo.addons.payment_adyen.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self.create_transaction('direct')
        url = self._build_url(AdyenController._webhook_url)
        with patch(
            'odoo.addons.payment_adyen.controllers.main.AdyenController'
            '._verify_notification_signature'
        ):
            self._make_json_request(url, data=self.webhook_notification_batch_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_adyen.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self.create_transaction('direct')
        url = self._build_url(AdyenController._webhook_url)
        with patch(
            'odoo.addons.payment_adyen.controllers.main.AdyenController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_json_request(url, data=self.webhook_notification_batch_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_webhook_notification_with_valid_signature(self):
        """ Test the verification of a webhook notification with a valid signature. """
        tx = self.create_transaction('direct')
        self._assert_does_not_raise(
            Forbidden,
            AdyenController._verify_notification_signature,
            self.webhook_notification_payload,
            tx,
        )

    @mute_logger('odoo.addons.payment_adyen.controllers.main')
    def test_reject_webhook_notification_with_missing_signature(self):
        """ Test the verification of a webhook notification with a missing signature. """
        payload = dict(self.webhook_notification_payload, additionalData={'hmacSignature': None})
        tx = self.create_transaction('direct')
        self.assertRaises(Forbidden, AdyenController._verify_notification_signature, payload, tx)

    @mute_logger('odoo.addons.payment_adyen.controllers.main')
    def test_reject_webhook_notification_with_invalid_signature(self):
        """ Test the verification of a webhook notification with an invalid signature. """
        payload = dict(self.webhook_notification_payload, additionalData={'hmacSignature': 'dummy'})
        tx = self.create_transaction('direct')
        self.assertRaises(Forbidden, AdyenController._verify_notification_signature, payload, tx)

    def test_adyen_neutralize(self):
        self.env['payment.acquirer']._neutralize()

        self.assertEqual(self.acquirer.adyen_merchant_account, False)
        self.assertEqual(self.acquirer.adyen_api_key, False)
        self.assertEqual(self.acquirer.adyen_hmac_key, False)
