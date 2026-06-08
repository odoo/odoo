from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ar_stock.tests.test_l10n_ar_delivery_guide import (
    TestArDeliveryGuide,
)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestArDeliveryGuideBatch(TestArDeliveryGuide):
    """ Tests for the multi-record / batch delivery guide."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cron = cls.env.ref('l10n_ar_stock.ir_cron_l10n_ar_send_delivery_guide')

    @staticmethod
    def _stub_render(recordset, _pdf_action):
        """ Patch target for `_l10n_ar_render_delivery_guide_pdfs` so cron tests
        don't shell out to wkhtmltopdf. Bound to the recordset via `patch.object`. """
        return {p.id: b'%PDF-stub' for p in recordset}

    # === l10n_ar_action_create_delivery_guide (multi) === #

    def test_create_delivery_guide_multi(self):
        """ Generating delivery guides on a recordset assigns a unique number to each picking. """
        pickings = self.get_stock_pickings(count=3)
        pickings.l10n_ar_action_create_delivery_guide()

        numbers = pickings.mapped('l10n_ar_delivery_guide_number')
        self.assertEqual(len(set(numbers)), 3, "Each picking should get a distinct delivery guide number.")
        self.assertTrue(all(numbers), "All pickings should have a delivery guide number.")
        for picking in pickings:
            self.assertTrue(picking.l10n_ar_cai_data, "CAI data should be stored on each picking.")

    def test_create_delivery_guide_collects_errors(self):
        """ When some pickings are ineligible the error message lists each offender; no number is assigned. """
        ok_picking = self.get_stock_picking()
        already_done = self.get_stock_picking()
        already_done.l10n_ar_action_create_delivery_guide()
        existing_number = already_done.l10n_ar_delivery_guide_number

        with self.assertRaisesRegex(UserError, rf"{already_done.name}.*already have a delivery guide"):
            (ok_picking | already_done).l10n_ar_action_create_delivery_guide()

        self.assertFalse(
            ok_picking.l10n_ar_delivery_guide_number,
            "When validation fails, no picking in the batch should be mutated.",
        )
        self.assertEqual(
            already_done.l10n_ar_delivery_guide_number, existing_number,
            "An already-generated number must not be overwritten.",
        )

    # === l10n_ar_action_send_delivery_guide_batch === #

    def test_send_batch_queues_records(self):
        """ The batch send action queues records on the cron and returns a notification. """
        pickings = self.get_stock_pickings(count=3)
        pickings.l10n_ar_action_create_delivery_guide()

        action = pickings.l10n_ar_action_send_delivery_guide(do_async=True)

        self.assertEqual(action['tag'], 'display_notification')
        for picking in pickings:
            self.assertEqual(picking.l10n_ar_delivery_guide_cron_user_id, self.env.user)

    def test_send_batch_validation_errors(self):
        """ Validation collects per-picking failures (no number, no email, already queued). """
        no_number = self.get_stock_picking()  # done but no guide number generated yet
        no_email_partner = self.env['res.partner'].create({'name': 'No Email Co'})
        no_email = self.get_stock_picking(stock_picking_args={'partner_id': no_email_partner.id})
        no_email.l10n_ar_action_create_delivery_guide()

        with self.assertRaisesRegex(UserError, "No delivery guide has been generated yet"):
            (no_number | no_email).l10n_ar_action_send_delivery_guide(do_async=True)

    def test_send_batch_already_queued(self):
        """ A picking already queued for sending cannot be re-queued. """
        picking = self.get_stock_picking()
        picking.l10n_ar_action_create_delivery_guide()
        picking.l10n_ar_action_send_delivery_guide(do_async=True)

        with self.assertRaisesRegex(UserError, "already queued"):
            picking.l10n_ar_action_send_delivery_guide(do_async=True)

    # === Cron processing === #

    def test_cron_sends_grouped_per_user(self):
        """ The cron sends queued guides, marks them processed, and clears state per user. """
        pickings = self.get_stock_pickings(count=2)
        pickings.l10n_ar_action_create_delivery_guide()
        pickings.l10n_ar_action_send_delivery_guide(do_async=True)

        StockPicking = self.env.registry['stock.picking']
        with patch.object(
            StockPicking, '_l10n_ar_render_delivery_guide_pdfs', self._stub_render,
        ), self.mock_mail_gateway(), self.enter_registry_test_mode():
            self.cron.method_direct_trigger()

        # One mail per picking
        self.assertEqual(len(self._new_mails), 2)
        # State cleared once the user has no more pending records
        for picking in pickings:
            self.assertFalse(picking.l10n_ar_delivery_guide_cron_user_id)

    def test_cron_respects_batch_size(self):
        """ The cron only processes `batch_size` records per call; the rest stay queued. """
        pickings = self.get_stock_pickings(count=3)
        pickings.l10n_ar_action_create_delivery_guide()
        pickings.l10n_ar_action_send_delivery_guide(do_async=True)

        StockPicking = self.env.registry['stock.picking']
        IrCron = self.env.registry['ir.cron']
        # method_direct_trigger doesn't accept kwargs, so call the cron method
        # directly. That bypasses the registry-test-mode cursor swap, so stub
        # _commit_progress to avoid its forbidden cr.commit().
        with patch.object(
            StockPicking, '_l10n_ar_render_delivery_guide_pdfs', self._stub_render,
        ), patch.object(IrCron, '_commit_progress'), self.mock_mail_gateway():
            self.env['stock.picking']._cron_l10n_ar_send_delivery_guide(batch_size=2)

        remaining = pickings.filtered('l10n_ar_delivery_guide_cron_user_id')
        self.assertEqual(len(remaining), 1)

    def test_cron_noop_when_queue_empty(self):
        """ Cron is a no-op when nothing is queued. """
        # Should not raise nor send anything.
        with self.mock_mail_gateway(), self.enter_registry_test_mode():
            self.cron.method_direct_trigger()
        self.assertFalse(self._new_mails)

    def test_cron_dequeues_invalid_records(self):
        """ When a queued picking becomes invalid before the cron fires, it is
        dequeued (cron user cleared, chatter note logged) while valid ones are still sent. """
        no_email_partner = self.env['res.partner'].create({'name': 'Will Lose Email', 'email': 'temp@test.com'})
        valid = self.get_stock_picking()
        invalid = self.get_stock_picking(stock_picking_args={'partner_id': no_email_partner.id})
        (valid | invalid).l10n_ar_action_create_delivery_guide()
        (valid | invalid).l10n_ar_action_send_delivery_guide(do_async=True)

        # Simulate field change after queueing: remove email from the partner.
        no_email_partner.email = False

        StockPicking = self.env.registry['stock.picking']
        with patch.object(
            StockPicking, '_l10n_ar_render_delivery_guide_pdfs', self._stub_render,
        ), self.mock_mail_gateway(), self.enter_registry_test_mode():
            self.cron.method_direct_trigger()

        # Valid picking: sent and dequeued.
        self.assertEqual(len(self._new_mails), 1)
        self.assertFalse(valid.l10n_ar_delivery_guide_cron_user_id)

        # Invalid picking: dequeued with chatter note, no mail sent.
        self.assertFalse(invalid.l10n_ar_delivery_guide_cron_user_id)
        chatter_messages = invalid.message_ids.filtered(
            lambda m: 'no email address' in (m.body or ''),
        )
        self.assertTrue(chatter_messages, "A chatter note should explain why the record was dequeued.")

    def test_render_fallback_on_batch_failure(self):
        """ If batched PDF rendering fails, the helper falls back to per-record rendering. """
        pickings = self.get_stock_pickings(count=2)
        pickings.l10n_ar_action_create_delivery_guide()

        report_action = self.env.ref('l10n_ar_stock.action_delivery_guide_report_pdf')
        IrActionsReport = self.env.registry['ir.actions.report']

        call_counter = {'pre': 0, 'render': 0}

        boom_msg = "simulated batch failure"

        def boom_pre(*_args, **_kwargs):
            call_counter['pre'] += 1
            raise UserError(boom_msg)

        def fake_render(*_args, **_kwargs):
            call_counter['render'] += 1
            return (b'%PDF-fallback', 'pdf')

        with patch.object(IrActionsReport, '_pre_render_qweb_pdf', boom_pre), \
             patch.object(IrActionsReport, '_render_qweb_pdf', fake_render):
            result = pickings._l10n_ar_render_delivery_guide_pdfs(report_action)

        self.assertEqual(call_counter['pre'], 1)
        self.assertEqual(call_counter['render'], 2)
        self.assertEqual(set(result.keys()), set(pickings.ids))
        self.assertTrue(all(v == b'%PDF-fallback' for v in result.values()))
