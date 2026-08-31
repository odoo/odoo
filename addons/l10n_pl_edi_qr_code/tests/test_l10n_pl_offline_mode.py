import base64
from contextlib import contextmanager
from datetime import date, timedelta, timezone
from unittest.mock import Mock, patch

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from odoo import fields, tools
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi.tests.test_l10n_pl_edi import TestL10nPlEdi
from odoo.addons.l10n_pl_edi_qr_code.tools.ksef_api_service import (
    KsefOfflineApiService,
    KSeFTimeoutError,
)
from odoo.addons.l10n_pl_edi_qr_code.tools.ksef_latarnia_service import KsefLatarniaService


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
class TestL10nPlOfflineMode(TestL10nPlEdi):

    offline_cron_xmlid = 'l10n_pl_edi_qr_code.cron_l10n_pl_edi_send_offline'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def read_certificate_file(filename):
            path = f'l10n_pl_edi_qr_code/tests/certificate/{filename}'
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

    def test_ksef_request_timeout_remains_distinguishable(self):
        service = KsefOfflineApiService(self.company)

        with (
            patch('odoo.addons.l10n_pl_edi.tools.ksef_api_service.requests.request', side_effect=requests.Timeout),
            mute_logger('odoo.addons.l10n_pl_edi.tools.ksef_api_service'),
            self.assertRaises(KSeFTimeoutError),
        ):
            service._make_request('POST', 'https://example.invalid')

    def test_find_invoice_in_session_uses_the_xml_hash(self):
        service = KsefOfflineApiService(self.company)
        expected = {'invoiceHash': 'EXPECTED', 'status': {'code': 200}}

        with patch.object(service, '_get_session_invoices', side_effect=[
            {'invoices': [{'invoiceHash': 'OTHER'}], 'continuationToken': 'NEXT'},
            {'invoices': [expected]},
        ]) as get_status:
            invoice = service.find_invoice_in_session('EXPECTED', session_id='SESSION-REF')

        self.assertEqual(invoice, expected)
        self.assertEqual(get_status.call_count, 2)

    def test_offline_send_sets_the_api_mode(self):
        service = KsefOfflineApiService(self.company)
        service.raw_symmetric_key = b'0' * 32
        service.raw_iv = b'0' * 16
        response = Mock()
        response.json.return_value = {'referenceNumber': 'OFFLINE-REF'}

        with patch(
            'odoo.addons.l10n_pl_edi.tools.ksef_api_service.KsefApiService._make_request',
            return_value=response,
        ) as request:
            service.send_offline_invoice(b'<Invoice/>')

        self.assertTrue(request.call_args.kwargs['json']['offlineMode'])

    def _prepare_offline_invoice(self, invoice=None):
        invoice = invoice or self.standard_invoice
        invoice.action_post()
        invoice.company_id.sudo().l10n_pl_edi_offline_certificate = self.offline_certificate
        invoice.action_l10n_pl_edi_prepare_offline()
        return invoice

    @contextmanager
    def _mock_offline_submission(self, **kwargs):
        if not kwargs:
            kwargs['return_value'] = {'referenceNumber': 'OFFLINE-REF'}
        with (
            patch.object(KsefOfflineApiService, 'open_ksef_session'),
            patch.object(KsefOfflineApiService, 'send_offline_invoice', **kwargs) as send_invoice,
        ):
            yield send_invoice

    def _run_offline_cron(self):
        self.env['account.move']._cron_l10n_pl_edi_send_offline()

    def _set_active_latarnia(self, message):
        self.latarnia_status.return_value = {'status': message['category'], 'messages': [message]}
        self.latarnia_messages.return_value = [message]

    def test_offline_prepare_and_send_preserves_xml(self):
        cron = self.env.ref(self.offline_cron_xmlid)
        cron.active = False
        expected_nextcall = fields.Datetime.now() + timedelta(minutes=20)
        invoice = self._prepare_offline_invoice()

        self.assertEqual(invoice.l10n_pl_edi_status, 'offline_pending')
        self.assertTrue(cron.active)
        self.assertGreaterEqual(cron.nextcall, expected_nextcall)
        self.assertTrue(invoice.invoice_pdf_report_id)
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

        with self._mock_offline_submission() as send_offline_invoice:
            self._run_offline_cron()

        send_offline_invoice.assert_called_once_with(xml_content)
        self.assertEqual(invoice.l10n_pl_edi_status, 'sent')
        self.assertEqual(invoice.l10n_pl_edi_ref, 'OFFLINE-REF')
        self.assertEqual(invoice._l10n_pl_edi_get_xml_bytes(), xml_content)
        self.assertFalse(cron.active)

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

    def test_offline_preparation_requires_supported_posted_invoice(self):
        with self.assertRaisesRegex(UserError, 'Only posted Polish customer invoices'):
            self.standard_invoice.action_l10n_pl_edi_prepare_offline()

        self.standard_invoice.action_post()
        with self.assertRaisesRegex(UserError, 'Configure a valid KSeF Offline certificate'):
            self.standard_invoice.action_l10n_pl_edi_prepare_offline()

        credit_note = self.standard_invoice.copy({'move_type': 'out_refund'})
        credit_note.action_post()
        credit_note.company_id.sudo().l10n_pl_edi_offline_certificate = self.offline_certificate
        with self.assertRaisesRegex(UserError, 'Only posted Polish customer invoices'):
            credit_note.action_l10n_pl_edi_prepare_offline()

    def test_cancel_offline_removes_frozen_documents(self):
        invoice = self._prepare_offline_invoice()
        xml_attachment = invoice.l10n_pl_edi_attachment_id
        pdf_attachment = invoice.invoice_pdf_report_id

        invoice.action_l10n_pl_edi_cancel_offline()

        self.assertFalse(invoice.l10n_pl_edi_status)
        self.assertFalse(invoice.l10n_pl_edi_offline_deadline)
        self.assertFalse(invoice.l10n_pl_edi_offline_next_attempt)
        self.assertFalse(xml_attachment.exists())
        self.assertFalse(pdf_attachment.exists())
        self.assertFalse(self.env.ref(self.offline_cron_xmlid).active)

    def test_submitted_offline_invoice_cannot_be_canceled(self):
        invoice = self._prepare_offline_invoice()
        invoice.l10n_pl_edi_ref = 'OFFLINE-REF'

        with self.assertRaisesRegex(UserError, 'submission has not started'):
            invoice.action_l10n_pl_edi_cancel_offline()

    def test_offline_retries_only_log_the_first_failure(self):
        invoice = self._prepare_offline_invoice()
        message_count = len(invoice.message_ids)

        with patch.object(KsefOfflineApiService, 'open_ksef_session', side_effect=UserError('KSeF unavailable')):
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

        with patch.object(KsefOfflineApiService, 'open_ksef_session') as open_session:
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(
            move.l10n_pl_edi_offline_deadline,
            move._l10n_pl_edi_add_working_days(event_end.date(), 1),
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
            move._l10n_pl_edi_add_working_days(latest_end.date(), 7),
        )
        self.assertEqual(move.l10n_pl_edi_status, 'offline_pending')

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

        with patch.object(KsefOfflineApiService, 'open_ksef_session') as open_session:
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(move.l10n_pl_edi_status, 'offline_pending')
        self.assertGreater(move.l10n_pl_edi_offline_next_attempt, now)

    def test_total_failure_ends_the_submission_queue(self):
        move = self._create_pending_offline_moves(1)
        now = fields.Datetime.now()
        message = self._latarnia_message(
            'TOTAL_FAILURE', 'FAILURE_START', 1003, now - timedelta(hours=1),
        )
        self._set_active_latarnia(message)

        with patch.object(KsefOfflineApiService, 'open_ksef_session') as open_session:
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(move.l10n_pl_edi_status, 'offline_no_submission')
        self.assertFalse(move.l10n_pl_edi_offline_deadline)
        self.assertFalse(move.l10n_pl_edi_offline_next_attempt)
        self.assertFalse(self.env.ref(self.offline_cron_xmlid).active)

    def test_total_failure_prevents_offline24_preparation(self):
        self.standard_invoice.action_post()
        self.standard_invoice.company_id.sudo().l10n_pl_edi_offline_certificate = self.offline_certificate
        self.latarnia_status.return_value = {'status': 'TOTAL_FAILURE'}

        with self.assertRaisesRegex(UserError, 'total failure'):
            self.standard_invoice.action_l10n_pl_edi_prepare_offline()

        self.assertFalse(self.standard_invoice.l10n_pl_edi_status)
        self.assertFalse(self.standard_invoice.l10n_pl_edi_attachment_id)

    def test_latarnia_failure_does_not_block_ksef_submission(self):
        move = self._create_pending_offline_moves(1)
        self.latarnia_status.return_value = None
        self.latarnia_messages.return_value = None

        with self._mock_offline_submission() as send_offline_invoice:
            self._run_offline_cron()

        send_offline_invoice.assert_called_once()
        self.assertEqual(move.l10n_pl_edi_status, 'sent')

    def test_offline_queue_waits_for_company_rate_limit(self):
        move = self._create_pending_offline_moves(1)
        next_send = fields.Datetime.now() + timedelta(minutes=5)
        self.company.sudo().l10n_pl_edi_offline_next_send = next_send

        with (
            patch.object(KsefOfflineApiService, 'open_ksef_session') as open_session,
            self.capture_triggers(self.offline_cron_xmlid) as captured_triggers,
        ):
            self._run_offline_cron()

        open_session.assert_not_called()
        self.assertEqual(move.l10n_pl_edi_offline_next_attempt, next_send)
        self.assertEqual(len(captured_triggers.records), 1)

    def test_offline_cron_stays_active_until_a_future_retry(self):
        move = self._create_pending_offline_moves(1)
        move.l10n_pl_edi_offline_next_attempt = fields.Datetime.now() + timedelta(hours=1)

        self._run_offline_cron()

        self.assertTrue(self.env.ref(self.offline_cron_xmlid).active)

    def test_offline_queue_processes_one_invoice_per_company(self):
        moves = self._create_pending_offline_moves(2)
        other_move = self._create_pending_offline_moves(1, self.company_2)

        with self._mock_offline_submission() as send_offline_invoice:
            self._run_offline_cron()

        self.assertEqual(send_offline_invoice.call_count, 2)
        self.assertEqual(len((moves | other_move).filtered(
            lambda move: move.l10n_pl_edi_status == 'sent'
        )), 2)
        self.assertEqual(len(moves.filtered(
            lambda move: move.l10n_pl_edi_status == 'offline_pending'
        )), 1)

    def test_offline_queue_processes_the_earliest_deadline_first(self):
        moves = self._create_pending_offline_moves(2)
        moves[0].l10n_pl_edi_offline_deadline = date(2026, 4, 8)
        moves[1].l10n_pl_edi_offline_deadline = date(2026, 4, 7)

        with self._mock_offline_submission():
            self._run_offline_cron()

        self.assertEqual(moves[0].l10n_pl_edi_status, 'offline_pending')
        self.assertEqual(moves[1].l10n_pl_edi_status, 'sent')

    def test_offline_queue_schedules_next_invoice_after_success(self):
        moves = self._create_pending_offline_moves(2)
        expected_next_send = fields.Datetime.now() + timedelta(minutes=1)

        with (
            self._mock_offline_submission() as send_offline_invoice,
            self.capture_triggers(self.offline_cron_xmlid) as captured_triggers,
        ):
            self._run_offline_cron()

        self.assertEqual(send_offline_invoice.call_count, 1)
        self.assertEqual(moves[0].l10n_pl_edi_status, 'sent')
        self.assertEqual(moves[1].l10n_pl_edi_status, 'offline_pending')
        self.assertGreaterEqual(self.company.l10n_pl_edi_offline_next_send, expected_next_send)
        self.assertEqual(
            moves[1].l10n_pl_edi_offline_next_attempt,
            self.company.l10n_pl_edi_offline_next_send,
        )
        self.assertEqual(len(captured_triggers.records), 1)

    def test_offline_queue_stops_after_first_failure(self):
        moves = self._create_pending_offline_moves(2)

        with self._mock_offline_submission(side_effect=UserError('KSeF unavailable')) as send_offline_invoice:
            self._run_offline_cron()

        self.assertEqual(send_offline_invoice.call_count, 1)
        self.assertEqual(moves[0].l10n_pl_edi_status, 'offline_failed')
        self.assertEqual(moves[1].l10n_pl_edi_status, 'offline_pending')
        self.assertGreater(moves[1].l10n_pl_edi_offline_next_attempt, fields.Datetime.now())

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
                KsefOfflineApiService,
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
            ) as send_offline_invoice,
            patch.object(
                KsefOfflineApiService,
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

        self.assertEqual(send_offline_invoice.call_count, 1)
        self.assertEqual(invoice.l10n_pl_edi_status, 'rejected')
        self.assertEqual(invoice.l10n_pl_edi_ref, 'OFFLINE-REF')
