from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_xendit.controllers.main import XenditController
from odoo.addons.payment_xendit.tests.common import XenditCommon

@tagged('post_install', '-at_install')
class TestRefundFlows(XenditCommon, PaymentHttpCommon):

    @mute_logger(
        'odoo.addons.payment_xendit.models.payment_transaction',
        'odoo.addons.payment_xendit.controllers.main'
    )
    def test_webhook_refund_data_trigger_processing(self):
        self._create_transaction('redirect', state='done')
        self._create_transaction('redirect', provider_reference='RFD-00001', reference="Refund")
        url = self._build_url(XenditController._webhook_url)

        with patch(
            'odoo.addons.payment_xendit.controllers.main.XenditController'
            '._xendit_verify_notification_signature'
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_json_request(url, data=self.webhook_notification_data_refund)
        handle_notification_data_mock.assert_called_once()

    @mute_logger(
        'odoo.addons.payment_xendit.models.payment_provider',
        'odoo.addons.payment_xendit.models.payment_transaction',
    )
    def test_refund_non_tokenized_payment(self):
        """ If the transaction is not using the token, then check if it's passing REFUND api_obj"""
        source_tx = self._create_transaction('redirect', state='done')

        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request'
        ) as xendit_req_mock:
            source_tx._send_refund_request(amount_to_refund=source_tx.amount)
        xendit_req_mock.assert_called_once()
        args = xendit_req_mock.call_args.args
        self.assertEqual(args[0], 'REFUND')

    @mute_logger(
        'odoo.addons.payment_xendit.models.payment_provider',
        'odoo.addons.payment_xendit.models.payment_transaction',
    )
    def test_refund_tokenized_payment(self):
        """ If the transaction is not using the token, then check if it's passing REFUND api_obj"""
        token = self._create_token()
        source_tx = self._create_transaction('redirect', state='done', token_id=token.id)

        with patch(
            'odoo.addons.payment_xendit.models.payment_provider.PaymentProvider'
            '._xendit_make_request'
        ) as xendit_req_mock:
            source_tx._send_refund_request(amount_to_refund=source_tx.amount)
        xendit_req_mock.assert_called_once()
        args = xendit_req_mock.call_args.args
        self.assertEqual(args[0], 'CARD_REFUND')
