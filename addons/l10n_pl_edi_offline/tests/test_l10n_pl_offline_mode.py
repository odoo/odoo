import base64
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from itertools import count
from unittest.mock import patch

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from odoo import fields, tools
from odoo.exceptions import UserError
from odoo.tests import freeze_time, tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError, KSeFTimeoutError
from odoo.addons.l10n_pl_edi.tests.test_l10n_pl_edi import TestL10nPlEdiCommon
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService
from odoo.addons.l10n_pl_edi_offline.models.account_move import OFFLINE_BATCH_SIZE
from odoo.addons.l10n_pl_edi_offline.tools.ksef_latarnia_service import KsefLatarniaService


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestKsefLatarniaService(TransactionCase):

    def test_test_mode_ignores_latarnia_outage_scenarios(self):
        parameters = self.env['ir.config_parameter'].sudo()
        parameters.set_param('l10n_pl_edi_ksef.mode', 'test')
        service = KsefLatarniaService(self.env)

        with patch.object(service, '_get') as request:
            self.assertEqual(service.get_status(), {'status': 'AVAILABLE'})
            self.assertEqual(service.get_messages(), [])
            request.assert_not_called()

        parameters.set_param('l10n_pl_edi_ksef.mode', 'prod')
        service = KsefLatarniaService(self.env)
        with patch.object(
            service,
            '_get',
            return_value={'status': 'TOTAL_FAILURE'},
        ):
            self.assertEqual(service.get_status(), {'status': 'TOTAL_FAILURE'})


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlOfflineMode(TestL10nPlEdiCommon):

    offline_cron_xmlid = 'l10n_pl_edi_offline.cron_l10n_pl_edi_send_offline'
    status_cron_xmlid = 'l10n_pl_edi.cron_auto_checks_the_polish_invoice_status'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def read_certificate_file(filename):
            path = f'l10n_pl_edi_offline/tests/certificate/{filename}'
            with tools.file_open(path, mode='rb') as file:
                return base64.b64encode(file.read())

        key_record = cls.env['certificate.key'].create({
            'company_id': cls.company.id,
            'name': 'l10n_pl_edi_test_offline.key',
            'content': read_certificate_file('l10n_pl_edi_test_offline.key'),
        })
        cls.offline_certificate = cls.env['certificate.certificate'].create({
            'company_id': cls.company.id,
            'name': 'l10n_pl_edi_test_offline.pem',
            'content': read_certificate_file('l10n_pl_edi_test_offline.pem'),
            'private_key_id': key_record.id,
        })

    def setUp(self):
        super().setUp()
        self.latarnia_status = self.startPatcher(patch.object(
            KsefLatarniaService,
            'get_status',
            return_value={'status': 'AVAILABLE'},
        ))
        self.latarnia_messages = self.startPatcher(patch.object(
            KsefLatarniaService,
            'get_messages',
            return_value=[],
        ))

    def _prepare_offline_invoice(self, invoice=None):
        invoice = invoice or self.standard_invoice
        invoice.action_post()
        invoice.company_id.sudo().l10n_pl_edi_offline_certificate = self.offline_certificate
        invoice._l10n_pl_edi_prepare_offline()
        return invoice

    @contextmanager
    def _mock_offline_submission(self, **kwargs):
        if not kwargs:
            kwargs['return_value'] = {'referenceNumber': 'OFFLINE-REF'}
        with (
            patch.object(KsefApiService, 'open_ksef_session'),
            patch.object(KsefApiService, 'send_invoice', **kwargs) as send_invoice,
        ):
            yield send_invoice

    def _run_offline_cron(self):
        self.env['account.move']._cron_l10n_pl_edi_send_offline()

    def _set_active_latarnia(self, message):
        self.latarnia_status.return_value = {'status': message['category'], 'messages': [message]}
        self.latarnia_messages.return_value = [message]

    def test_offline_prepare_and_send_preserves_xml(self):
        with self.capture_triggers(self.offline_cron_xmlid) as captured_triggers:
            invoice = self._prepare_offline_invoice()

        self.assertEqual(invoice.l10n_pl_edi_status, 'offline_pending')
        self.assertEqual(len(captured_triggers.records), 1)
        self.assertFalse(invoice.invoice_pdf_report_id)
        xml_content = invoice._l10n_pl_edi_get_xml_bytes()
        certificate_link = invoice._l10n_pl_edi_generate_certificate_qr_link()
        signed_payload, encoded_signature = certificate_link.removeprefix(
            'https://'
        ).rsplit('/', 1)
        signature = base64.urlsafe_b64decode(
            encoded_signature + '=' * (-len(encoded_signature) % 4)
        )
        certificate = x509.load_pem_x509_certificate(base64.b64decode(
            invoice.company_id.sudo().l10n_pl_edi_offline_certificate.pem_certificate
        ))
        public_key = certificate.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                signature,
                signed_payload.encode(),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
                hashes.SHA256(),
            )
        else:
            self.assertIsInstance(public_key, ec.EllipticCurvePublicKey)
            public_key.verify(
                signature,
                signed_payload.encode(),
                ec.ECDSA(hashes.SHA256()),
            )

        with (
            self._mock_offline_submission() as send_invoice,
            self.capture_triggers(self.status_cron_xmlid) as status_triggers,
        ):
            self._run_offline_cron()

        send_invoice.assert_called_once_with(xml_content, offline_mode=True)
        self.assertEqual(invoice.l10n_pl_edi_status, 'sent')
        self.assertEqual(invoice.l10n_pl_edi_ref, 'OFFLINE-REF')
        self.assertEqual(invoice._l10n_pl_edi_get_xml_bytes(), xml_content)
        self.assertEqual(len(status_triggers.records), 1)

    def test_offline_deadline_skips_weekends_and_public_holidays(self):
        self.standard_invoice.invoice_date = date(2026, 4, 3)

        invoice = self._prepare_offline_invoice()

        self.assertEqual(invoice.l10n_pl_edi_offline_deadline, date(2026, 4, 7))
        self.assertEqual(
            invoice._l10n_pl_edi_get_offline_deadline(date(2026, 12, 23)),
            date(2026, 12, 28),
        )
        self.assertEqual(
            invoice._l10n_pl_edi_get_offline_deadline(date(2026, 12, 31)),
            date(2027, 1, 4),
        )

    def test_offline_report_identifies_unsubmitted_document(self):
        invoice = self._prepare_offline_invoice()

        report_html = self.env['ir.actions.report']._render_qweb_html(
            'account.account_invoices', invoice.ids,
        )[0]

        self.assertIn(b'OFFLINE', report_html)
        self.assertIn(b'CERTYFIKAT', report_html)

    def test_accepted_offline_report_keeps_both_codes(self):
        invoice = self._prepare_offline_invoice()
        ksef_number = '7492091229-20260403-000000000000-00'
        invoice.write({'l10n_pl_edi_status': 'accepted', 'l10n_pl_edi_number': ksef_number})

        # The QR code images are not what is tested, only that the report shows both.
        with patch.object(self.env.registry['ir.actions.report'], 'barcode', return_value=b'QR'):
            report_html = self.env['ir.actions.report']._render_qweb_html(
                'account.account_invoices', invoice.ids,
            )[0]

        self.assertIn(b'id="ksef_verification_code"', report_html)
        self.assertIn(b'id="ksef_certificate_code"', report_html)
        self.assertIn(ksef_number.encode(), report_html)
        self.assertNotIn(b'OFFLINE', report_html)

    def test_offline_preparation_requires_supported_posted_invoice(self):
        with self.assertRaisesRegex(UserError, 'Only posted Polish customer invoices'):
            self.standard_invoice._l10n_pl_edi_prepare_offline()

        self.standard_invoice.action_post()
        with self.assertRaisesRegex(UserError, 'Configure a valid KSeF Offline certificate'):
            self.standard_invoice._l10n_pl_edi_prepare_offline()

        bill = self._create_invoice(move_type='in_invoice', post=True)
        bill.company_id.sudo().l10n_pl_edi_offline_certificate = self.offline_certificate
        with self.assertRaisesRegex(UserError, 'Only posted Polish customer invoices'):
            bill._l10n_pl_edi_prepare_offline()

    def test_offline_invoice_cannot_be_reset_to_draft_or_canceled(self):
        invoice = self._prepare_offline_invoice()

        with self.assertRaisesRegex(UserError, 'issued in Offline24'):
            invoice.button_draft()
        with self.assertRaisesRegex(UserError, 'issued in Offline24'):
            invoice.button_cancel()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_pl_edi_status, 'offline_pending')
        self.assertTrue(invoice.l10n_pl_edi_attachment_id)

    def test_offline_retries_only_log_the_first_failure(self):
        invoice = self._prepare_offline_invoice()
        message_count = len(invoice.message_ids)

        with patch.object(KsefApiService, 'open_ksef_session', side_effect=UserError('KSeF unavailable')):
            self._run_offline_cron()
            self.assertEqual(len(invoice.message_ids), message_count + 1)

            invoice.l10n_pl_edi_offline_next_attempt = fields.Datetime.now()
            self.company.sudo().l10n_pl_edi_offline_next_send = False
            self._run_offline_cron()

        self.assertEqual(len(invoice.message_ids), message_count + 1)

    def _create_pending_offline_moves(self, count, company=None):
        company = company or self.company
        return self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'company_id': company.id,
            'l10n_pl_edi_status': 'offline_pending',
            'l10n_pl_edi_offline_deadline': self.env['account.move']._l10n_pl_edi_get_offline_deadline(fields.Date.today()),
            'l10n_pl_edi_offline_next_attempt': fields.Datetime.now(),
            'l10n_pl_edi_offline_prepared_at': fields.Datetime.now(),
        } for _ in range(count)])

    @staticmethod
    def _latarnia_message(category, message_type, event_id, start, end=None):
        message = {
            'id': f'EVENT-{event_id}',
            'category': category,
            'type': message_type,
            'eventId': event_id,
            'version': 1,
            'start': start.replace(tzinfo=timezone.utc).isoformat(),
        }
        if end:
            message['end'] = end.replace(tzinfo=timezone.utc).isoformat()
        return message

    def test_maintenance_adjusts_deadline_and_suspends_submission(self):
        move = self._create_pending_offline_moves(1)
        now = fields.Datetime.now()
        event_end = now + timedelta(hours=2)
        message = self._latarnia_message(
            'MAINTENANCE', 'MAINTENANCE_ANNOUNCEMENT', 1000,
            now - timedelta(hours=1), event_end,
        )
        self._set_active_latarnia(message)

        with patch.object(KsefApiService, 'open_ksef_session') as open_session:
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(
            move.l10n_pl_edi_offline_deadline,
            move._l10n_pl_edi_add_working_days(move._l10n_pl_edi_get_warsaw_date(event_end), 1),
        )
        self.assertEqual(move.l10n_pl_edi_offline_next_attempt, event_end)

    def test_failure_announcements_use_latest_seven_day_deadline(self):
        move = self._create_pending_offline_moves(1)
        now = fields.Datetime.now()
        move.write({
            'l10n_pl_edi_offline_prepared_at': now - timedelta(days=10),
            'l10n_pl_edi_offline_next_attempt': now + timedelta(hours=1),
        })
        first_end = now - timedelta(days=4)
        latest_end = now - timedelta(days=1)
        messages = [
            self._latarnia_message(
                'FAILURE', 'FAILURE_END', 1001,
                now - timedelta(days=5), first_end,
            ),
            self._latarnia_message(
                'FAILURE', 'FAILURE_END', 1002,
                now - timedelta(days=2), latest_end,
            ),
        ]
        self.latarnia_messages.return_value = messages

        self._run_offline_cron()

        self.assertEqual(
            move.l10n_pl_edi_offline_deadline,
            move._l10n_pl_edi_add_working_days(move._l10n_pl_edi_get_warsaw_date(latest_end), 7),
        )
        self.assertEqual(move.l10n_pl_edi_status, 'offline_pending')

    def test_total_failure_end_uses_seven_day_deadline(self):
        move = self._create_pending_offline_moves(1)
        now = fields.Datetime.now()
        move.write({
            'l10n_pl_edi_offline_prepared_at': now - timedelta(days=5),
            'l10n_pl_edi_offline_deadline': (now - timedelta(days=1)).date(),
            'l10n_pl_edi_offline_next_attempt': now + timedelta(hours=1),
        })
        event_end = now - timedelta(hours=12)
        self.latarnia_messages.return_value = [self._latarnia_message(
            'TOTAL_FAILURE', 'FAILURE_END', 1003,
            now - timedelta(days=2), event_end,
        )]

        self._run_offline_cron()

        self.assertEqual(
            move.l10n_pl_edi_offline_deadline,
            move._l10n_pl_edi_add_working_days(move._l10n_pl_edi_get_warsaw_date(event_end), 7),
        )
        self.assertEqual(move.l10n_pl_edi_status, 'offline_pending')

    def test_failure_end_counts_the_deadline_from_the_warsaw_date(self):
        move = self._create_pending_offline_moves(1)
        move.write({
            'l10n_pl_edi_offline_prepared_at': datetime(2026, 3, 9, 9, 0),
            'l10n_pl_edi_offline_deadline': date(2026, 3, 10),
            'l10n_pl_edi_offline_next_attempt': fields.Datetime.now() + timedelta(hours=1),
        })
        # 23:30 UTC on Tuesday 10 March is 00:30 on Wednesday 11 March in Warsaw.
        self.latarnia_messages.return_value = [self._latarnia_message(
            'FAILURE', 'FAILURE_END', 1004,
            datetime(2026, 3, 9, 10, 0), datetime(2026, 3, 10, 23, 30),
        )]

        self._run_offline_cron()

        self.assertEqual(move.l10n_pl_edi_offline_deadline, date(2026, 3, 20))

    def test_failure_after_the_submission_period_does_not_change_the_deadline(self):
        move = self._create_pending_offline_moves(1)
        now = fields.Datetime.now()
        deadline = (now - timedelta(days=2)).date()
        move.write({
            'l10n_pl_edi_offline_prepared_at': now - timedelta(days=5),
            'l10n_pl_edi_offline_deadline': deadline,
            'l10n_pl_edi_offline_next_attempt': now + timedelta(hours=1),
        })
        self.latarnia_messages.return_value = [self._latarnia_message(
            'FAILURE', 'FAILURE_END', 1001,
            now - timedelta(days=1), now - timedelta(hours=12),
        )]

        self._run_offline_cron()

        self.assertEqual(move.l10n_pl_edi_offline_deadline, deadline)

    def test_active_failure_suspends_submission_until_an_end_announcement(self):
        move = self._create_pending_offline_moves(1)
        now = fields.Datetime.now()
        message = self._latarnia_message(
            'FAILURE', 'FAILURE_START', 1001, now - timedelta(hours=1),
        )
        self._set_active_latarnia(message)

        with patch.object(KsefApiService, 'open_ksef_session') as open_session:
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(move.l10n_pl_edi_status, 'offline_pending')
        self.assertGreater(move.l10n_pl_edi_offline_next_attempt, now)

    def test_total_failure_pauses_the_submission_queue(self):
        move = self._create_pending_offline_moves(1)
        now = fields.Datetime.now()
        message = self._latarnia_message(
            'TOTAL_FAILURE', 'FAILURE_START', 1003, now - timedelta(hours=1),
        )
        self._set_active_latarnia(message)

        with (
            patch.object(KsefApiService, 'open_ksef_session') as open_session,
            self.capture_triggers(self.offline_cron_xmlid) as captured_triggers,
        ):
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(move.l10n_pl_edi_status, 'offline_pending')
        self.assertGreater(move.l10n_pl_edi_offline_next_attempt, now)
        self.assertEqual(captured_triggers.records.call_at, move.l10n_pl_edi_offline_next_attempt)

        self.latarnia_status.return_value = {'status': 'AVAILABLE'}
        self.latarnia_messages.return_value = [self._latarnia_message(
            'TOTAL_FAILURE', 'FAILURE_END', 1003, now - timedelta(hours=1), now,
        )]
        move.l10n_pl_edi_offline_next_attempt = now
        with self._mock_offline_submission() as send_invoice:
            self._run_offline_cron()

        send_invoice.assert_called_once()
        self.assertEqual(move.l10n_pl_edi_status, 'sent')

    def test_total_failure_allows_offline24_preparation(self):
        self.latarnia_status.return_value = {'status': 'TOTAL_FAILURE'}

        invoice = self._prepare_offline_invoice()

        self.assertEqual(invoice.l10n_pl_edi_status, 'offline_pending')
        self.assertTrue(invoice.l10n_pl_edi_attachment_id)
        self.assertTrue(invoice.l10n_pl_edi_offline_deadline)

    def test_latarnia_failure_does_not_block_ksef_submission(self):
        move = self._create_pending_offline_moves(1)
        self.latarnia_status.return_value = None
        self.latarnia_messages.return_value = None

        with self._mock_offline_submission() as send_invoice:
            self._run_offline_cron()

        send_invoice.assert_called_once()
        self.assertEqual(move.l10n_pl_edi_status, 'sent')

    def test_offline_queue_waits_for_company_rate_limit(self):
        move = self._create_pending_offline_moves(1)
        next_send = fields.Datetime.now() + timedelta(minutes=5)
        self.company.sudo().l10n_pl_edi_offline_next_send = next_send

        with (
            patch.object(KsefApiService, 'open_ksef_session') as open_session,
            self.capture_triggers(self.offline_cron_xmlid) as captured_triggers,
        ):
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(move.l10n_pl_edi_offline_next_attempt, next_send)
        self.assertEqual(len(captured_triggers.records), 1)

    def test_offline_queue_sends_a_batch_per_company(self):
        moves = self._create_pending_offline_moves(OFFLINE_BATCH_SIZE + 2)
        other_move = self._create_pending_offline_moves(1, self.company_2)

        with self._mock_offline_submission() as send_invoice:
            self._run_offline_cron()

        self.assertEqual(send_invoice.call_count, OFFLINE_BATCH_SIZE + 1)
        self.assertEqual(other_move.l10n_pl_edi_status, 'sent')
        self.assertEqual(moves[:OFFLINE_BATCH_SIZE].mapped('l10n_pl_edi_status'), ['sent'] * OFFLINE_BATCH_SIZE)
        self.assertEqual(moves[OFFLINE_BATCH_SIZE:].mapped('l10n_pl_edi_status'), ['offline_pending'] * 2)

    def test_offline_queue_processes_the_earliest_deadline_first(self):
        moves = self._create_pending_offline_moves(OFFLINE_BATCH_SIZE + 1)
        moves[0].l10n_pl_edi_offline_deadline += timedelta(days=1)

        with self._mock_offline_submission():
            self._run_offline_cron()

        self.assertEqual(moves[0].l10n_pl_edi_status, 'offline_pending')
        self.assertEqual(set(moves[1:].mapped('l10n_pl_edi_status')), {'sent'})

    def test_offline_queue_schedules_next_batch_after_success(self):
        now = fields.Datetime.now()
        with freeze_time(now):
            moves = self._create_pending_offline_moves(OFFLINE_BATCH_SIZE + 1)

            with (
                self._mock_offline_submission() as send_invoice,
                self.capture_triggers(self.offline_cron_xmlid) as captured_triggers,
            ):
                self._run_offline_cron()

        self.assertEqual(send_invoice.call_count, OFFLINE_BATCH_SIZE)
        self.assertEqual(moves[-1].l10n_pl_edi_status, 'offline_pending')
        self.assertEqual(self.company.l10n_pl_edi_offline_next_send, now + timedelta(minutes=10))
        self.assertEqual(moves[-1].l10n_pl_edi_offline_next_attempt, now + timedelta(minutes=10))
        self.assertEqual(captured_triggers.records.call_at, now + timedelta(minutes=10))

    def test_offline_queue_failure_only_defers_the_failed_invoice(self):
        now = fields.Datetime.now()
        with freeze_time(now):
            moves = self._create_pending_offline_moves(2)

            with (
                self._mock_offline_submission(side_effect=[
                    UserError('KSeF unavailable'),
                    {'referenceNumber': 'OFFLINE-REF'},
                ]) as send_invoice,
                self.capture_triggers(self.offline_cron_xmlid) as captured_triggers,
            ):
                self._run_offline_cron()

        self.assertEqual(send_invoice.call_count, 2)
        self.assertEqual(moves[0].l10n_pl_edi_status, 'offline_failed')
        self.assertEqual(moves[0].l10n_pl_edi_offline_next_attempt, now + timedelta(hours=1))
        self.assertEqual(moves[1].l10n_pl_edi_status, 'sent')
        self.assertEqual(self.company.l10n_pl_edi_offline_next_send, now + timedelta(minutes=10))
        self.assertEqual(captured_triggers.records.call_at, now + timedelta(hours=1))

    def test_offline_queue_rate_limit_stops_the_company_batch(self):
        now = fields.Datetime.now()
        with freeze_time(now):
            moves = self._create_pending_offline_moves(3)

            with self._mock_offline_submission(side_effect=[
                {'referenceNumber': 'OFFLINE-REF'},
                KSeFRateLimitError('Too Many Requests', retry_after=120),
            ]) as send_invoice:
                self._run_offline_cron()

        self.assertEqual(send_invoice.call_count, 2)
        self.assertEqual(moves.mapped('l10n_pl_edi_status'), ['sent', 'offline_failed', 'offline_pending'])
        self.assertEqual(moves[1:].mapped('l10n_pl_edi_offline_next_attempt'), [now + timedelta(seconds=120)] * 2)
        self.assertEqual(self.company.l10n_pl_edi_offline_next_send, now + timedelta(seconds=120))

    def test_offline_queue_respects_retry_after(self):
        move = self._create_pending_offline_moves(1)
        retry_after = 120
        expected_retry = fields.Datetime.now() + timedelta(seconds=retry_after)

        with self._mock_offline_submission(
            side_effect=KSeFRateLimitError('Too Many Requests', retry_after=retry_after),
        ):
            self._run_offline_cron()

        self.assertEqual(move.l10n_pl_edi_status, 'offline_failed')
        self.assertGreaterEqual(move.l10n_pl_edi_offline_next_attempt, expected_retry)
        self.assertGreaterEqual(self.company.l10n_pl_edi_offline_next_send, expected_retry)

    def test_offline_timeout_recovers_accepted_submission(self):
        invoice = self._prepare_offline_invoice()
        self.company.sudo().l10n_pl_edi_session_id = 'SESSION-REF'
        recovered_status = {
            'referenceNumber': 'OFFLINE-REF',
            'ksefNumber': '7492091229-20260403-000000000000-00',
            'status': {'code': 200},
        }

        with (
            self._mock_offline_submission(side_effect=KSeFTimeoutError('The KSeF request timed out.')),
            patch.object(
                KsefApiService,
                'find_invoice_in_session',
                return_value=recovered_status,
            ) as find_invoice,
        ):
            self._run_offline_cron()

        self.assertEqual(invoice.l10n_pl_edi_status, 'accepted')
        self.assertEqual(invoice.l10n_pl_edi_ref, 'OFFLINE-REF')
        self.assertEqual(invoice.l10n_pl_edi_number, recovered_status['ksefNumber'])
        find_invoice.assert_called_once()

    def test_offline_timeout_reconciles_before_resending(self):
        invoice = self._prepare_offline_invoice()
        self.company.sudo().l10n_pl_edi_session_id = 'SESSION-REF'
        rejected_status = {
            'referenceNumber': 'OFFLINE-REF',
            'status': {'code': 450},
        }

        with (
            self._mock_offline_submission(
                side_effect=KSeFTimeoutError('The KSeF request timed out.'),
            ) as send_invoice,
            patch.object(
                KsefApiService,
                'find_invoice_in_session',
                side_effect=[None, rejected_status],
            ),
        ):
            self._run_offline_cron()
            self.assertEqual(invoice.l10n_pl_edi_status, 'offline_failed')
            self.assertEqual(invoice.l10n_pl_edi_session_id, 'SESSION-REF')

            invoice.l10n_pl_edi_offline_next_attempt = fields.Datetime.now()
            self.company.sudo().l10n_pl_edi_offline_next_send = False
            self._run_offline_cron()

        self.assertEqual(send_invoice.call_count, 1)
        self.assertEqual(invoice.l10n_pl_edi_status, 'rejected')
        self.assertEqual(invoice.l10n_pl_edi_ref, 'OFFLINE-REF')

    def _send_to_ksef(self, invoice, **request_kwargs):
        """ Run the KSeF sending step of Send & Print with requests.request mocked, return its sending data. """
        invoices_data = {invoice: {'extra_edis': {'pl_ksef'}, 'invoice_edi_format': None}}
        with (
            patch('odoo.addons.l10n_pl_edi.tools.ksef_api_service.requests.request', **request_kwargs),
            mute_logger('odoo.addons.l10n_pl_edi.tools.ksef_api_service'),
        ):
            self.env['account.move.send']._call_web_service_before_invoice_pdf_render(invoices_data)
        return invoices_data[invoice]

    def _prepare_sending(self, offline_certificate=True):
        self.standard_invoice.action_post()
        self.company.sudo().write({
            'l10n_pl_edi_offline_certificate': offline_certificate and self.offline_certificate.id,
            'l10n_pl_edi_session_key': base64.b64encode(b'0' * 32),
            'l10n_pl_edi_session_iv': base64.b64encode(b'0' * 16),
        })
        self.startPatcher(patch.object(KsefApiService, 'open_ksef_session'))
        return self.standard_invoice

    @staticmethod
    def _ksef_response(status_code):
        response = requests.Response()
        response.status_code = status_code
        response._content = b'{"exception": "KSeF answer"}'
        return response

    def _assert_issued_in_offline24(self, invoice, sending_data):
        self.assertNotIn('error', sending_data)
        self.assertEqual(invoice.l10n_pl_edi_status, 'offline_pending')
        self.assertTrue(invoice.l10n_pl_edi_attachment_id)
        self.assertTrue(invoice.l10n_pl_edi_offline_deadline)
        self.assertTrue(invoice.message_ids.filtered(
            lambda message: 'KSeF was unavailable' in message.body
        ))
        self.assertTrue(self.env['ir.cron.trigger'].search([
            ('cron_id', '=', self.env.ref(self.offline_cron_xmlid).id),
        ]))

    def _assert_sending_error(self, invoice, sending_data, error):
        self.assertIn(error, sending_data['error']['errors'][0])
        self.assertFalse(invoice.l10n_pl_edi_status)
        self.assertFalse(invoice.l10n_pl_edi_attachment_id)

    def test_ksef_timeout_falls_back_to_offline24(self):
        invoice = self._prepare_sending()

        sending_data = self._send_to_ksef(invoice, side_effect=requests.Timeout)

        self._assert_issued_in_offline24(invoice, sending_data)

    def test_ksef_server_error_falls_back_to_offline24(self):
        invoice = self._prepare_sending()

        sending_data = self._send_to_ksef(invoice, return_value=self._ksef_response(503))

        self._assert_issued_in_offline24(invoice, sending_data)

    def test_ksef_session_failure_falls_back_to_offline24(self):
        self.standard_invoice.action_post()
        self.company.sudo().write({
            'l10n_pl_edi_offline_certificate': self.offline_certificate.id,
            'l10n_pl_edi_session_id': 'PREVIOUS-SESSION',
        })
        invoices_data = {self.standard_invoice: {'extra_edis': {'pl_ksef'}, 'invoice_edi_format': None}}
        AccountMove = self.env.registry['account.move']

        with (
            patch('odoo.addons.l10n_pl_edi.tools.ksef_api_service.requests.request', side_effect=requests.ConnectionError),
            mute_logger('odoo.addons.l10n_pl_edi.tools.ksef_api_service'),
            patch.object(KsefApiService, 'send_invoice') as send_invoice,
            patch.object(
                AccountMove, '_l10n_pl_edi_render_xml',
                autospec=True, side_effect=AccountMove._l10n_pl_edi_render_xml,
            ) as render_xml,
        ):
            self.env['account.move.send']._call_web_service_before_invoice_pdf_render(invoices_data)

        send_invoice.assert_not_called()
        render_xml.assert_called_once()
        self._assert_issued_in_offline24(self.standard_invoice, invoices_data[self.standard_invoice])
        self.assertFalse(self.standard_invoice.l10n_pl_edi_session_id)

    def test_ksef_timeout_freezes_the_sent_xml_and_finds_it_in_its_session(self):
        invoice = self._prepare_sending()
        self.company.sudo().l10n_pl_edi_session_id = 'ONLINE-SESSION'
        invoices_data = {invoice: {'extra_edis': {'pl_ksef'}, 'invoice_edi_format': None}}
        AccountMove = self.env.registry['account.move']
        render_xml = AccountMove._l10n_pl_edi_render_xml
        renderings = count()

        def render_a_new_xml(move):
            # Each rendering differs, like the creation timestamp of the XML does.
            return f"{render_xml(move)}<!-- rendering {next(renderings)} -->"

        with (
            patch.object(AccountMove, '_l10n_pl_edi_render_xml', autospec=True, side_effect=render_a_new_xml),
            patch.object(
                KsefApiService, 'send_invoice', side_effect=KSeFTimeoutError('The KSeF request timed out.'),
            ) as send_invoice,
        ):
            self.env['account.move.send']._call_web_service_before_invoice_pdf_render(invoices_data)

        sent_xml = send_invoice.call_args.args[0]
        self._assert_issued_in_offline24(invoice, invoices_data[invoice])
        self.assertEqual(invoice._l10n_pl_edi_get_xml_bytes(), sent_xml)
        self.assertEqual(invoice.l10n_pl_edi_session_id, 'ONLINE-SESSION')

        received_status = {
            'referenceNumber': 'ONLINE-REF',
            'ksefNumber': '7492091229-20260123-000000000000-00',
            'status': {'code': 200},
        }
        with (
            self._mock_offline_submission() as send_offline,
            patch.object(
                KsefApiService, 'find_invoice_in_session', return_value=received_status,
            ) as find_invoice,
        ):
            self._run_offline_cron()

        find_invoice.assert_called_once_with(
            KsefApiService.get_invoice_hash(sent_xml), session_id='ONLINE-SESSION',
        )
        send_offline.assert_not_called()
        self.assertEqual(invoice.l10n_pl_edi_status, 'accepted')
        self.assertEqual(invoice.l10n_pl_edi_ref, 'ONLINE-REF')
        self.assertEqual(invoice.l10n_pl_edi_number, received_status['ksefNumber'])

    def test_ksef_unavailable_without_offline_certificate_keeps_the_error(self):
        invoice = self._prepare_sending(offline_certificate=False)

        sending_data = self._send_to_ksef(invoice, side_effect=requests.Timeout)

        self._assert_sending_error(invoice, sending_data, 'KSeF API Error')

    def test_ksef_rejection_does_not_fall_back_to_offline24(self):
        invoice = self._prepare_sending()

        sending_data = self._send_to_ksef(invoice, return_value=self._ksef_response(400))

        self._assert_sending_error(invoice, sending_data, 'KSeF answer')

    def test_ksef_rate_limit_does_not_fall_back_to_offline24(self):
        invoice = self._prepare_sending()

        sending_data = self._send_to_ksef(invoice, return_value=self._ksef_response(429))

        self._assert_sending_error(invoice, sending_data, 'Too Many Requests')

    def _post_credit_note(self, invoice):
        self.env['account.move.reversal'].create({
            'reason': 'Correction',
            'journal_id': invoice.journal_id.id,
            'move_ids': invoice.ids,
        }).refund_moves()
        credit_note = invoice.reversal_move_ids
        credit_note.action_post()
        return credit_note

    def test_ksef_timeout_issues_the_credit_note_in_offline24(self):
        invoice = self._prepare_sending()
        ksef_number = '7492091229-20260123-000000000000-00'
        invoice.write({'l10n_pl_edi_status': 'accepted', 'l10n_pl_edi_number': ksef_number})
        credit_note = self._post_credit_note(invoice)

        sending_data = self._send_to_ksef(credit_note, side_effect=requests.Timeout)

        self._assert_issued_in_offline24(credit_note, sending_data)
        xml_content = credit_note._l10n_pl_edi_get_xml_bytes()
        self.assertEqual(self._get_xml_value(xml_content, '//ns:RodzajFaktury'), 'KOR')
        self.assertEqual(
            self._get_xml_value(xml_content, '//ns:DaneFaKorygowanej/ns:NrKSeFFaKorygowanej'), ksef_number,
        )

        with self._mock_offline_submission() as send_invoice:
            self._run_offline_cron()

        send_invoice.assert_called_once_with(xml_content, offline_mode=True)
        self.assertEqual(credit_note.l10n_pl_edi_status, 'sent')
        self.assertEqual(credit_note.l10n_pl_edi_ref, 'OFFLINE-REF')

    def test_credit_note_of_a_pending_offline24_invoice_is_not_sent(self):
        invoice = self._prepare_offline_invoice()
        credit_note = self._post_credit_note(invoice)
        wizard = self.env['account.move.send.wizard'].with_company(self.company).create({
            'move_id': credit_note.id,
            'extra_edi_checkboxes': {'pl_ksef': {'checked': True}},
        })

        with (
            patch.object(KsefApiService, 'open_ksef_session') as open_session,
            patch.object(KsefApiService, 'send_invoice') as send_invoice,
            self.assertRaisesRegex(
                UserError, f'The corrected invoice {invoice.name} is waiting for its Offline24 submission to KSeF',
            ),
        ):
            wizard.action_send_and_print()

        open_session.assert_not_called()
        send_invoice.assert_not_called()
        self.assertFalse(credit_note.l10n_pl_edi_status)
        self.assertFalse(credit_note.l10n_pl_edi_attachment_id)

    def test_offline24_fallback_sends_one_pdf_with_both_qr_codes(self):
        invoice = self._prepare_sending()

        with (
            patch('odoo.addons.l10n_pl_edi.tools.ksef_api_service.requests.request', side_effect=requests.Timeout),
            mute_logger('odoo.addons.l10n_pl_edi.tools.ksef_api_service'),
            # The QR code images are not what is tested, only that the report shows both.
            patch.object(self.env.registry['ir.actions.report'], 'barcode', return_value=b'QR'),
        ):
            self.env['account.move.send.wizard'].with_company(self.company).create({
                'move_id': invoice.id,
                'extra_edi_checkboxes': {'pl_ksef': {'checked': True}},
            }).action_send_and_print()

        self.assertEqual(invoice.l10n_pl_edi_status, 'offline_pending')
        self.assertTrue(invoice.is_move_sent)
        pdf_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', invoice.id),
            ('res_field', '=', 'invoice_pdf_report_file'),
        ])
        self.assertEqual(len(pdf_attachments), 1)
        self.assertEqual(pdf_attachments, invoice.invoice_pdf_report_id)
        self.assertEqual(invoice.message_main_attachment_id, pdf_attachments)
        self.assertIn(b'id="ksef_verification_code"', pdf_attachments.raw)
        self.assertIn(b'id="ksef_certificate_code"', pdf_attachments.raw)
