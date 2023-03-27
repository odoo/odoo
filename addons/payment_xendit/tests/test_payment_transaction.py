from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_xendit.tests.common import XenditCommon

@tagged('post_install', '-at_install')
class TestPaymentTransaction(PaymentHttpCommon, XenditCommon):

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._process_notification_data(self.webhook_notification_data_invoice)
        self.assertEqual(tx.state, 'done')

    def test_get_tx_from_notification_data_invoice(self):
        """ Test that finding transaction should be by doing matching external_id and reference from notification data"""
        tx = self._create_transaction(flow='redirect', reference='TEST0001')
        tx_found = self.env['payment.transaction']._get_tx_from_notification_data('xendit', self.webhook_notification_data_invoice)
        self.assertEqual(tx.id, tx_found.id)

    def test_get_tx_from_notification_data_refund(self):
        """ When notification data is for refund, finding the transaction should be by provider reference"""
        tx = self._create_transaction(flow='redirect', reference='TEST0002', provider_reference='RFD-00001')
        tx_found = self.env['payment.transaction']._get_tx_from_notification_data('xendit', self.webhook_notification_data_refund)
        self.assertEqual(tx.id, tx_found.id)
