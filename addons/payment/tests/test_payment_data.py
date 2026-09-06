# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestPaymentData(PaymentCommon):
    def setUp(self):
        super().setUp()
        self.tx = self._create_transaction("redirect")
        self.payment_data = self.env["payment.data"].create({
            "transaction_id": self.tx.id,
            "payload": {"dummy": "data"},
        })

        self.IrCron = self.registry["ir.cron"]
        self.PaymentData = self.registry["payment.data"]
        self.PaymentTransaction = self.registry["payment.transaction"]

    def test_processing_cron_processes_new_payment_data(self):
        self._run_processing()
        self.assertEqual(self.process_mock.call_count, 1)

    def test_processing_cron_skips_errored_payment_data(self):
        self.payment_data.errored = True
        self._run_processing()
        self.assertEqual(self.process_mock.call_count, 0)

    def test_processing_cron_locks_records(self):
        with (
            patch.object(
                self.PaymentTransaction,
                "try_lock_for_update",
                return_value=self.payment_data.transaction_id,
            ) as tx_lock_mock,
            patch.object(
                self.PaymentData,
                "try_lock_for_update",
                autospec=True,  # Prevent unlink() from mistaking the mock for an api.ondelete hook
                return_value=self.payment_data,
            ) as data_lock_mock,
        ):
            self._run_processing()
        self.assertEqual(tx_lock_mock.call_count, 2)  # In _cron_process & _post_process_transaction
        self.assertEqual(data_lock_mock.call_count, 1)

    def test_processing_cron_locks_source_transaction(self):
        child_tx = self.tx._create_child_transaction(self.tx.amount)
        self.payment_data.transaction_id = child_tx
        with (
            patch.object(
                self.PaymentTransaction,
                "try_lock_for_update",
                autospec=True,
                return_value=child_tx + self.tx,
            ) as try_lock_for_update_mock,
            patch.object(self.PaymentData, "_post_process_transaction"),
        ):
            self._run_processing()
        self.assertEqual(try_lock_for_update_mock.call_args[0][0], child_tx + self.tx)

    def test_processing_cron_skips_processing_when_failing_to_acquire_locks(self):
        with (
            patch.object(self.PaymentTransaction, "try_lock_for_update", return_value=None),
            patch.object(
                self.PaymentData,
                "search",
                # Find the record on the first call, but avoid infinite loops with the next calls
                side_effect=iter([self.payment_data, self.payment_data.browse([])]),
            ),
            patch.object(self.PaymentTransaction, "_process") as process_mock,
        ):
            self._run_processing()
        self.assertEqual(process_mock.call_count, 0)

    def test_processing_cron_releases_locks_when_skipping_processing(self):
        with (
            patch.object(self.PaymentTransaction, "try_lock_for_update", return_value=None),
            patch.object(
                self.PaymentData,
                "search",
                # Find the record on the first call, but avoid infinite loops with the next calls
                side_effect=iter([self.payment_data, self.payment_data.browse([])]),
            ),
            patch.object(self.IrCron, "_rollback_progress") as rollback_mock,
        ):
            self._run_processing()
        self.assertEqual(rollback_mock.call_count, 1)

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_releases_locks_when_processing_fails(self):
        self.process_mock.side_effect = Exception
        with patch.object(self.IrCron, "_rollback_progress") as rollback_mock:
            self._run_processing()
        self.assertEqual(rollback_mock.call_count, 1)

    def test_processing_cron_bypasses_write_guard(self):
        process_context = {}
        self.process_mock.side_effect = lambda tx, _data: process_context.update(tx.env.context)
        self._run_processing()
        self.assertTrue(process_context.get("payment_safe_write"))

    def test_processing_cron_deletes_processed_payment_data(self):
        self._run_processing()
        self.assertFalse(self.payment_data.exists())

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_flags_payment_data_when_processing_fails(self):
        self.process_mock.side_effect = Exception
        self._run_processing()
        self.assertTrue(self.payment_data.errored)

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_preserves_processing_when_post_processing_fails(self):
        self.post_process_mock.side_effect = Exception
        self._run_processing()
        self.assertFalse(self.payment_data.exists())

    def test_processing_cron_post_processes_transactions(self):
        self._run_processing()
        self.assertEqual(self.post_process_mock.call_count, 1)

    def test_processing_cron_post_processes_source_transaction(self):
        child_tx = self.tx._create_child_transaction(self.tx.amount)
        self.payment_data.transaction_id = child_tx
        self._run_processing()
        self.assertTrue(self.tx.is_post_processed)

    def test_processing_cron_skips_post_processing_of_post_processed_transactions(self):
        self._update_transaction(self.tx, is_post_processed=True)
        self._run_processing()
        self.assertFalse(self.post_process_mock.call_args.args[0])

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_defers_to_cron_when_post_processing_fails(self):
        post_processing_cron = self.env.ref("payment.post_processing_cron")
        post_processing_cron.active = True  # Allow triggering the cron
        trigger_count = self.env["ir.cron.trigger"].search_count([
            ("cron_id", "=", post_processing_cron.id)
        ])
        self.post_process_mock.side_effect = Exception
        self._run_processing()
        new_trigger_count = self.env["ir.cron.trigger"].search_count([
            ("cron_id", "=", post_processing_cron.id)
        ])
        self.assertEqual(new_trigger_count, trigger_count + 1)
        self.assertFalse(self.tx.is_post_processed)  # Post-processing is left to the cron

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_notifies_client_on_post_processing_success(self):
        with patch.object(self.PaymentTransaction, "_notify_status") as notify_status_mock:
            self._run_processing()
        self.assertEqual(notify_status_mock.call_count, 1)

    @mute_logger("odoo.addons.payment.models.payment_data")
    def test_processing_cron_notifies_client_on_post_processing_failure(self):
        self.post_process_mock.side_effect = Exception
        with patch.object(self.PaymentTransaction, "_notify_status") as notify_status_mock:
            self._run_processing()
        self.assertEqual(notify_status_mock.call_count, 1)
