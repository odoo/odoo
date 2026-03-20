# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged('post_install', '-at_install')
class TestRefundFlows(StripeCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_stripe.models.payment_transaction')
    def test_refund_id_is_set_as_provider_reference(self):
        """ Test that the id of the refund object is set as the provider reference of the refund
        transaction. """
        source_tx = self._create_transaction('redirect', state='done')
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value=self.refund_object,
        ):
            source_tx._refund()
        refund_tx = self.env['payment.transaction'].search(
            [('source_transaction_id', '=', source_tx.id)]
        )
        self.assertEqual(refund_tx.provider_reference, self.refund_object['id'])

    @mute_logger(
        'odoo.addons.payment_stripe.controllers.main',
        'odoo.addons.payment_stripe.models.payment_transaction',
    )
    def test_canceled_refund_webhook_notification_triggers_processing(self):
        """ Test that receiving a webhook notification for a refund cancellation
        (`charge.refund.updated` event) triggers the processing of the payment data. """
        source_tx = self._create_transaction('redirect', state='done')
        source_tx._create_child_transaction(
            source_tx.amount, is_refund=True, provider_reference=self.refund_object['id']
        )
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_json_request(url, data=self.canceled_refund_payment_data)
        self.assertEqual(process_mock.call_count, 1)
