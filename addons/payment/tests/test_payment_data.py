# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestPaymentData(PaymentCommon):
    def setUp(self):
        super().setUp()
        tx = self._create_transaction("redirect")
        self.payment_data = self.env["payment.data"].create({
            "transaction_id": tx.id,
            "payload": {"dummy": "data"},
        })

    def test_processing_cron_processes_new_payment_data(self):
        PaymentTransaction = self.registry["payment.transaction"]
        with patch.object(PaymentTransaction, "_process") as process_mock:
            self._run_processing()
        self.assertEqual(process_mock.call_count, 1)

    def test_processing_cron_skips_errored_payment_data(self):
        PaymentTransaction = self.registry["payment.transaction"]
        self.payment_data.errored = True
        with patch.object(PaymentTransaction, "_process") as process_mock:
            self._run_processing()
        self.assertEqual(process_mock.call_count, 0)

    def test_processing_cron_locks_records_before_processing(self):
        PaymentTransaction = self.registry["payment.transaction"]
        PaymentData = self.registry["payment.data"]
        with (
            patch.object(
                PaymentTransaction,
                "try_lock_for_update",
                return_value=self.payment_data.transaction_id,
            ) as tx_lock_mock,
            patch.object(
                PaymentData, "try_lock_for_update", return_value=self.payment_data
            ) as data_lock_mock,
            patch.object(PaymentTransaction, "_process"),
        ):
            self._run_processing()
        self.assertEqual(tx_lock_mock.call_count, 1)
        self.assertEqual(data_lock_mock.call_count, 1)

    def test_processing_cron_releases_locks_when_skipping_processing(self):
        PaymentTransaction = self.registry["payment.transaction"]
        PaymentData = self.registry["payment.data"]
        IrCron = self.registry["ir.cron"]
        with (
            patch.object(PaymentTransaction, "try_lock_for_update", return_value=None),
            patch.object(
                PaymentData,
                "search",
                # Find the record on the first call, but avoid infinite loops with the next calls
                side_effect=iter([self.payment_data, self.payment_data.browse([])]),
            ),
            patch.object(IrCron, "_rollback_progress") as rollback_mock,
        ):
            self._run_processing()
        self.assertEqual(rollback_mock.call_count, 1)

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_releases_locks_when_processing_fails(self):
        PaymentTransaction = self.registry["payment.transaction"]
        IrCron = self.registry["ir.cron"]
        with (
            patch.object(PaymentTransaction, "_process", side_effect=Exception),
            patch.object(IrCron, "_rollback_progress") as rollback_mock,
        ):
            self._run_processing()
        self.assertEqual(rollback_mock.call_count, 1)

    def test_processing_cron_bypasses_write_guard(self):

        def process_mock(tx, *_args):
            process_context.update(tx.env.context)

        PaymentTransaction = self.registry["payment.transaction"]
        process_context = {}
        with patch.object(PaymentTransaction, "_process", autospec=True, side_effect=process_mock):
            self._run_processing()
        self.assertTrue(process_context.get("payment_safe_write"))

    def test_processing_cron_deletes_processed_payment_data(self):
        self._run_processing()
        self.assertFalse(self.payment_data.exists())

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_flags_payment_data_when_processing_fails(self):
        PaymentTransaction = self.registry["payment.transaction"]
        with patch.object(PaymentTransaction, "_process", side_effect=Exception):
            self._run_processing()
        self.assertTrue(self.payment_data.errored)
