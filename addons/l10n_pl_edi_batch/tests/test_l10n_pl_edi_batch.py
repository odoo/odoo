import base64
import io
import math
import threading
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import requests

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import freeze_time, tagged
from odoo.tools import convert_file, file_open, mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi_batch import uninstall_hook
from odoo.addons.l10n_pl_edi_batch.models.batch_download import (
    HISTORIC_REQUEST_DELAY,
    TODAY_REQUEST_DELAY,
    exp_backoff_delay,
    ksef_midnight,
)
from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlEdiBatch(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.Batch = cls.env['l10n_pl_edi_batch.download']
        cls.Part = cls.env['l10n_pl_edi_batch.part']
        cls.encryption_data = {'raw_symmetric_key': 'S0VZ', 'encrypted_symmetric_key': 'RU5D', 'raw_iv': 'SVY='}

        # Disable KSeF on real companies, just enable it on tests.
        # Tests do rollback after they finish, and this will be re-enabled
        cls.env['res.company'].search([]).l10n_pl_edi_access_token = False
        cls.company.l10n_pl_edi_access_token = 'token'
        # as set by the company's first today request
        cls.company.l10n_pl_edi_batch_historic_date = fields.Date.today() - timedelta(days=1)
        cls.simple_accountman.email = 'accountman@example.com'

        cls.env['ir.config_parameter'].set_param('l10n_pl_edi_ksef.mode', 'test')
        cls.server_url = KsefApiServiceBatch(cls.company).api_url

        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            cls.xml_content = xml_file.read()

    # Helpers ------------------------------------------------------------------

    def _create_batch(self, name, content=None):
        return self.Batch.create({
            'name': name,
            'company_id': self.company.id,
            'date_from': '2026-11-01 00:00:00',
            'date_to': '2026-11-08 00:00:00',
            'content': content,
        })

    def _create_downloading_batch(self, part_count=2, now=None):
        now = now or fields.Datetime.now()
        batch = self._create_batch('downloading_batch', {
            'status': {'code': 200},
            'packageExpirationDate': (now + timedelta(days=1)).isoformat() + '+00:00',
        })
        for number in range(1, part_count + 1):
            self._add_part(batch, number)
        self._set_write_date(batch, now - timedelta(seconds=10))
        return batch

    def _create_downloaded_batch(self, name, now, historic=False):
        batch = self._create_batch(name, {'status': {'code': 200}})
        if historic:
            batch.write({'date_from': now - timedelta(days=9), 'date_to': now - timedelta(days=2)})
        else:
            batch.write({'date_from': now - timedelta(days=1), 'date_to': now})
        self._add_zip_parts(batch, self._make_zip({f'{name}-ksef-number.xml': self.xml_content}), count=1)
        self._set_write_date(batch, now - timedelta(seconds=10))
        return batch

    def _company_batches(self, company):
        return self.Batch.search([('company_id', '=', company.id)], order='id')

    def _set_write_date(self, batches, write_date):
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE l10n_pl_edi_batch_download SET write_date = %s WHERE id in %s",
            [write_date, batches._ids])
        batches.invalidate_recordset(['write_date'])

    def _add_part(self, batch, number, content=None):
        part = self.Part.create({
            'batch_id': batch.id,
            'part_number': number,
            'part_name': f'{batch.name}-{number:03}.zip.aes',
            'download_method': 'GET',
            'download_url': f'{self.server_url}/{batch.name}-{number:03}.zip.aes',
        })
        if content:
            part._store_decrypted_file(content)
        return part

    def _add_zip_parts(self, batch, zip_bytes, count=2):
        """ Cut the ZIP in `count` slices, as KSeF does, and store them as
            downloaded parts.
        """
        size = math.ceil(len(zip_bytes) / count)
        parts = self.Part
        for number in range(1, count + 1):
            parts |= self._add_part(batch, number, zip_bytes[(number - 1) * size:number * size])
        return parts

    def _make_zip(self, files):
        """ The bytes of a ZIP with `files`, a dict of file name: content. """
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            for name, content in files.items():
                zip_file.writestr(name, content)
        return zip_stream.getvalue()

    def _search_xml_from_bill(self, bill):
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', bill.id),
            ('res_field', '=', 'l10n_pl_edi_attachment_file'),
            ('name', '=', f'KSeF-{bill.l10n_pl_edi_number}.xml'),
        ])

    def _search_imported(self):
        return self.env['account.move'].search([('l10n_pl_edi_number', '!=', False)])

    def _search_triggers_by_cron(self, name):
        cron = self.env.ref(f'l10n_pl_edi_batch.ir_cron_{name}')
        return self.env['ir.cron.trigger'].search([('cron_id', '=', cron.id)]).mapped('call_at')

    def _create_single_download_bill(self, day, status):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'l10n_pl_edi_number': f'5265877635-{day}-010080-DD2B5E-{status[:2]}',
            'l10n_pl_edi_status': status,
        })

    def _run_historic_cron(self, now):
        """ One run of the historic cron; the batch it requests is then done, so
            that the next run moves on.
        """
        batches_before = self._company_batches(self.company)
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        new_batch = self._company_batches(self.company) - batches_before
        new_batch.content = {'status': {'code': 200}}
        return new_batch

    def _assert_requested_again(self, failed_batch, now):
        """ The window of `failed_batch` is requested again 5 minutes later, by
            the historic cron, in a new batch.
        """
        self.assertIn(now + HISTORIC_REQUEST_DELAY, self._search_triggers_by_cron('request_historic'))
        with freeze_time(now + HISTORIC_REQUEST_DELAY), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertRecordValues(self._company_batches(self.company) - failed_batch, [{
            'date_from': failed_batch.date_from,
            'date_to': failed_batch.date_to,
            'state': 'requested',
        }])

    # Test computed fields -----------------------------------------------------

    @freeze_time('2026-11-10 12:00:00')
    def test_date_expiry_and_is_expired_fields(self):
        requested_batch = self._create_batch('requested')
        self.assertFalse(requested_batch.date_expiry)
        self.assertFalse(requested_batch.is_expired)

        ready_batch = self._create_batch('ready', {
            'status': {'code': 200},
            # Warsaw time (UTC+1): 13:00 UTC
            'packageExpirationDate': '2026-11-12T14:00:00+01:00',
        })
        self.assertEqual(ready_batch.date_expiry, datetime(2026, 11, 12, 13, 0, 0))
        self.assertFalse(ready_batch.is_expired)

        expired_batch = self._create_batch('expired', {
            'status': {'code': 200},
            'packageExpirationDate': '2026-11-09T12:00:00+00:00',
        })
        self.assertTrue(expired_batch.is_expired)

    def test_error_field(self):
        ready_batch = self._create_batch('ready', {
            'status': {
                'code': 200,
                'description': "Eksport zakonczony",
            },
            'package': {'invoiceCount': 3},
        })
        self.assertFalse(ready_batch.error)

        rejected_batch = self._create_batch('rejected', {
            'status': {
                'code': 415,
                'description': "Blad odszyfrowania",
                'details': ["Bad key"],
            },
        })
        self.assertEqual(rejected_batch.error, "415: Blad odszyfrowania\nBad key")

    def test_kind_field(self):
        now = fields.Datetime.now()
        historic_batch = self.Batch.create({
            'name': 'historic',
            'company_id': self.company.id,
            'date_from': now - timedelta(days=9),
            'date_to': now - timedelta(days=2),
        })
        self.assertEqual(historic_batch.kind, 'historic')

        today_batch = self.Batch.create({
            'name': 'today',
            'company_id': self.company.id,
            'date_from': now - timedelta(days=1),
            'date_to': now,
        })
        self.assertEqual(today_batch.kind, 'today')

    @freeze_time('2026-11-10 12:00:00')
    def test_state_field(self):
        ready = {'status': {'code': 200}, 'packageExpirationDate': '2026-11-12T12:00:00+00:00'}
        expired = {'status': {'code': 200}, 'packageExpirationDate': '2026-11-09T12:00:00+00:00'}
        requested_batch = self._create_batch('requested_batch')
        rejected_batch = self._create_batch('rejected_batch', {'status': {'code': 415}})
        odoo_error_batch = self._create_batch('odoo_error', {**ready, 'status': {'code': 999}})
        too_many_retries_batch = self._create_batch('too_many_retries_batch')
        too_many_retries_batch.retry_count = 10
        expired_missing_part_batch = self._create_batch('expired_missing_part_batch', expired)
        self._add_part(expired_missing_part_batch, 1)
        downloading_batch = self._create_downloading_batch(part_count=2)
        downloaded_batch = self._create_batch('downloaded_batch', ready)
        self._add_part(downloaded_batch, 1, content=b'decrypted zip slice')
        expired_downloaded_batch = self._create_batch('expired_downloaded_batch', expired)
        self._add_part(expired_downloaded_batch, 1, content=b'decrypted zip slice')
        done_batch = self._create_batch('done_batch', ready)
        empty_batch = self._create_batch('empty', {'status': {'code': 200}, 'package': {'invoiceCount': 0}})

        self.assertEqual(requested_batch.state, 'requested')
        self.assertEqual(rejected_batch.state, 'failed')
        self.assertEqual(odoo_error_batch.state, 'failed')
        self.assertEqual(too_many_retries_batch.state, 'failed')
        self.assertEqual(expired_missing_part_batch.state, 'failed')
        self.assertEqual(downloading_batch.state, 'downloading')
        self.assertEqual(downloaded_batch.state, 'downloaded')
        self.assertEqual(expired_downloaded_batch.state, 'downloaded')
        self.assertEqual(done_batch.state, 'done')
        self.assertEqual(empty_batch.state, 'done')

        # Searching on the computed state finds the same batches
        batches = self._company_batches(self.company)
        failed_batches = rejected_batch | odoo_error_batch | too_many_retries_batch | expired_missing_part_batch
        self.assertEqual(self.Batch.search([('state', '=', 'failed')]) & batches, failed_batches)
        self.assertEqual(
            self.Batch.search([('state', 'not in', ['done', 'failed'])]) & batches,
            requested_batch | downloading_batch | downloaded_batch | expired_downloaded_batch,
        )

    # Mock the KSeF service ----------------------------------------------------

    def _mock_ksef(self, json_answer):
        """ Stands in for KSeF: every request gets a 200 with `json_answer`;
            returns the mock, to read the requests sent.
        """
        response = MagicMock(status_code=200)
        response.json.return_value = json_answer
        return patch('odoo.addons.l10n_pl_edi.tools.ksef_api_service.requests.request', return_value=response)

    def _mock_part_downloads(self, error=None, content=b'slice'):
        """ Stands in for the storage of the parts: each one decrypts to
            `content`, unless the download fails.
        """
        return (
            patch.object(self.env.registry['l10n_pl_edi_batch.part'], '_decrypt_stream', lambda part, response: iter([content])),
            patch('odoo.addons.l10n_pl_edi_batch.models.batch_part.request', side_effect=error),
        )

    def _ready_answer(self, now, **package):
        """ KSeF's status answer for a package ready in one part; `package` adds
            or overrides its keys.
        """
        return {
            'status': {'code': 200},
            'packageExpirationDate': (now + timedelta(days=1)).isoformat() + '+00:00',
            'package': {
                'parts': [{'ordinalNumber': 1, 'partName': 'part-001.zip.aes', 'url': f'{self.server_url}/part-001.zip.aes', 'method': 'get'}],
                **package,
            },
        }

    def _mock_batch_requests(self, failing_companies=(), rate_limited=False):
        """ Stands in for the KSeF export request: a new reference number per
            call, unless the company fails or KSeF is rate-limited.
        """
        numbers = iter(range(1, 1000))

        def download_batch_request(service, date_from, date_to, encryption_data):
            if rate_limited:
                raise KSeFRateLimitError("Too Many Requests", retry_after=30)
            if service.company in failing_companies:
                raise UserError("KSeF API Error: 500")
            return {'referenceNumber': f'{service.company.name}-{next(numbers)}'}

        return patch.multiple(
            KsefApiServiceBatch,
            _create_encryption_data=lambda service: self.encryption_data,
            download_batch_request=download_batch_request,
        )

    # Test parts ---------------------------------------------------------------

    def test_parts(self):
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        first_part = self._add_part(ready_batch, 1, content=b'decrypted zip slice')
        second_part = self._add_part(ready_batch, 2)

        part_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'l10n_pl_edi_batch.part'),
            ('res_field', '=', 'decrypted_file'),
            ('res_id', 'in', (first_part | second_part).ids),
        ])
        self.assertEqual(len(part_attachments), 1)
        self.assertEqual(ready_batch.state, 'downloading')

        # When you delete parts, the attachments get deleted too
        ready_batch.unlink()
        self.assertFalse(part_attachments.exists())

    def test_part_slice_stored_without_mimetype_guess(self):
        zip_bytes = self._make_zip({'ksef-number.xml': b'<xml/>' * 1000})
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})

        # The first slice starts like a ZIP but isn't a whole one: stored as .zip, its type isn't guessed
        with self.assertNoLogs('odoo.tools.mimetypes', 'WARNING'):
            parts = self._add_zip_parts(ready_batch, zip_bytes, count=2)
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'l10n_pl_edi_batch.part'),
            ('res_field', '=', 'decrypted_file'),
            ('res_id', '=', parts[0].id),
        ])
        self.assertRecordValues(attachment, [{'name': 'ready-001.zip', 'mimetype': 'application/zip'}])
        self.assertEqual(ready_batch.state, 'downloaded')

    # Test import --------------------------------------------------------------

    def test_import_bills(self):
        zip_bytes = self._make_zip({
            'new-ksef-number.xml': self.xml_content,
            'known-ksef-number.xml': self.xml_content,
            '_metadata.json': '{}',
        })

        known_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'l10n_pl_edi_number': 'known-ksef-number',
        })
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, zip_bytes)
        self.assertEqual(ready_batch.state, 'downloaded')

        bills_before = self._search_imported()
        self.Batch._cron_import()
        new_bill = self._search_imported() - bills_before

        # One bill for the new KSeF number, with its XML attached as the single-invoice download does;
        # the known one is skipped
        self.assertRecordValues(new_bill, [{'l10n_pl_edi_number': 'new-ksef-number', 'l10n_pl_edi_status': 'fetched'}])

        attachment = self._search_xml_from_bill(new_bill)
        self.assertRecordValues(attachment, [{'raw': self.xml_content, 'description': 'KSeF Fetched Invoice XML'}])
        self.assertTrue(known_bill.exists())
        self.assertEqual(ready_batch.state, 'done')
        # The imported parts are deleted, with their decrypted files
        self.assertFalse(ready_batch.part_ids)

        # Nothing left to import: a second run does nothing
        self.Batch._cron_import()
        self.assertEqual(self._search_imported() - bills_before, new_bill)

    def test_import_bills_fills_half_fetched_bills(self):
        half_fetched_bill = self._create_single_download_bill('20260501', 'fetch_ready')
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, self._make_zip({
            f'{half_fetched_bill.l10n_pl_edi_number}.xml': self.xml_content,
            '_metadata.json': '{}',
        }))

        # The bill left half-fetched by the single download gets its XML, and no new bill is created
        bills_before = self._search_imported()
        self.Batch._cron_import()
        self.assertEqual(self._search_imported(), bills_before)
        self.assertEqual(half_fetched_bill.l10n_pl_edi_status, 'fetched')
        self.assertRecordValues(self._search_xml_from_bill(half_fetched_bill), [{'raw': self.xml_content}])

    def test_import_bills_relinks_the_xml_of_a_failed_single_download(self):
        failed_bill = self._create_single_download_bill('20260501', 'fetch_failed')
        old_xml = self.env['ir.attachment'].create({
            'name': f'KSeF-{failed_bill.l10n_pl_edi_number}.xml',
            'raw': b'<Faktura>old</Faktura>',
            'res_model': 'account.move',
            'res_id': failed_bill.id,
            'res_field': 'l10n_pl_edi_attachment_file',
        })
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, self._make_zip({f'{failed_bill.l10n_pl_edi_number}.xml': self.xml_content}))

        self.Batch._cron_import()

        # Only the imported XML is linked to the field; the old one stays attached to the bill
        new_xml = self._search_xml_from_bill(failed_bill)
        self.assertRecordValues(new_xml, [{'raw': self.xml_content}])
        self.assertEqual(failed_bill.l10n_pl_edi_attachment_id, new_xml)
        self.assertRecordValues(old_xml, [{'res_id': failed_bill.id, 'res_field': False}])

    def test_import_bills_links_xml_and_stores_pdf(self):
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, self._make_zip({'pdf-ksef-number.xml': self.xml_content}))

        with patch.object(
            self.env.registry['ir.actions.report'], '_render_qweb_pdf', return_value=(b'bill PDF', 'pdf'),
        ) as render_pdf:
            self.Batch._cron_import()
        bill = self.env['account.move'].search([('l10n_pl_edi_number', '=', 'pdf-ksef-number')])

        # The XML is linked to the bill as the single download does, so the PL tab and the KOD I QR code find it,
        # and the import from the attachment still fills the bill
        self.assertEqual(bill.l10n_pl_edi_status, 'fetched')
        self.assertTrue(bill.invoice_line_ids)
        self.assertEqual(bill.l10n_pl_edi_attachment_id, self._search_xml_from_bill(bill))
        self.assertEqual(bill._l10n_pl_edi_get_xml_bytes(), self.xml_content)
        render_pdf.assert_called_once()
        self.assertEqual(bill.invoice_pdf_report_id.raw, b'bill PDF')

    def test_import_bills_pdf_rendering_failure(self):
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, self._make_zip({'pdf-ksef-number.xml': self.xml_content}))

        with (
            patch.object(
                self.env.registry['ir.actions.report'], '_render_qweb_pdf', side_effect=UserError('PDF rendering failed'),
            ),
            mute_logger('odoo.addons.l10n_pl_edi_batch.models.batch_download'),
        ):
            self.Batch._cron_import()
        bill = self.env['account.move'].search([('l10n_pl_edi_number', '=', 'pdf-ksef-number')])

        # The bill is imported and fetched all the same, only the chatter tells the PDF is missing
        self.assertEqual(bill.l10n_pl_edi_status, 'fetched')
        self.assertTrue(bill.invoice_line_ids)
        self.assertTrue(bill.l10n_pl_edi_attachment_id)
        self.assertFalse(bill.invoice_pdf_report_id)
        self.assertTrue(bill.message_ids.filtered(
            lambda message: 'PDF visualization could not be generated' in message.body
        ))
        self.assertEqual(ready_batch.state, 'done')

    def test_import_bills_corrupt_zip(self):
        now = fields.Datetime.now().replace(microsecond=0)
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})

        # The parts are downloaded again, once the batch is due
        self._add_zip_parts(ready_batch, b'not a zip at all')
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertRecordValues(ready_batch, [{'state': 'downloading', 'retry_count': 1}])
        self.assertFalse(ready_batch.part_ids.with_context(bin_size=True).filtered('decrypted_file'))
        self.assertIn(now + exp_backoff_delay(1), self._search_triggers_by_cron('download'))

        # After the last retry, the batch fails, and its window is requested again
        ready_batch.part_ids.unlink()
        self._add_zip_parts(ready_batch, b'not a zip at all')
        ready_batch.retry_count = 9
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_import()
        self.assertEqual(ready_batch.state, 'failed')
        self.assertTrue(ready_batch.error.startswith("999: Odoo Error\nThe KSeF batch ZIP is corrupt"))
        self._assert_requested_again(ready_batch, now)

    def test_import_bills_corrupt_xml(self):
        now = fields.Datetime.now().replace(microsecond=0)
        xml_content = b'<Faktura>corrupt-ksef-number</Faktura>'
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_STORED) as zip_file:
            zip_file.writestr('corrupt-ksef-number.xml', xml_content)
        zip_bytes = bytearray(zip_stream.getvalue())
        position = zip_bytes.index(xml_content)
        zip_bytes[position] ^= 0xFF
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, bytes(zip_bytes), count=1)

        # The index reads fine, the file doesn't: no bill, and the parts are downloaded again
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertFalse(self.env['account.move'].search([('l10n_pl_edi_number', '=', 'corrupt-ksef-number')]))
        self.assertRecordValues(ready_batch, [{'state': 'downloading', 'retry_count': 1}])
        self.assertFalse(ready_batch.part_ids.with_context(bin_size=True).filtered('decrypted_file'))
        self.assertIn(now + exp_backoff_delay(1), self._search_triggers_by_cron('download'))

    def test_import_bills_bad_xmls(self):
        zip_bytes = self._make_zip({
            'unreadable-ksef-number.xml': b'<not xml',
            'failing-ksef-number.xml': self.xml_content,
            'good-ksef-number.xml': self.xml_content,
        })
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, zip_bytes)

        AccountMove = self.env.registry['account.move']
        decode_fa3_ksef = AccountMove._decode_fa3_ksef

        def failing_decoder(move, invoice, file_data, new=False):
            if file_data['filename'] == 'KSeF-failing-ksef-number.xml':
                raise ValueError("Unexpected tag")
            return decode_fa3_ksef(move, invoice, file_data, new)

        # The standard import catches the errors of each XML, and goes on with the next one
        with (
            patch.object(AccountMove, '_decode_fa3_ksef', failing_decoder),
            self.assertLogs('odoo.addons.account.models.account_move', 'ERROR'),
        ):
            self.Batch._cron_import()
        bills = self.env['account.move'].search([('l10n_pl_edi_number', 'like', '%-ksef-number')])
        bills_by_number = {bill.l10n_pl_edi_number: bill for bill in bills}
        self.assertEqual(ready_batch.state, 'done')
        self.assertTrue(bills_by_number['good-ksef-number'].invoice_line_ids)
        self.assertEqual(bills_by_number['good-ksef-number'].l10n_pl_edi_status, 'fetched')

        # The bills that failed are fetched too, blank: they keep their KSeF number and XML, so that they aren't
        # imported twice
        for number in ('unreadable-ksef-number', 'failing-ksef-number'):
            bill = bills_by_number[number]
            self.assertFalse(bill.invoice_line_ids, number)
            self.assertEqual(bill.l10n_pl_edi_status, 'fetched', number)
            self.assertTrue(self._search_xml_from_bill(bill), number)
        failing_messages = bills_by_number['failing-ksef-number'].message_ids.mapped('body')
        self.assertTrue(any("Error importing attachment" in body for body in failing_messages))
        # An unreadable XML only means no QR code: the PDF is still stored
        self.assertTrue(bills_by_number['unreadable-ksef-number'].invoice_pdf_report_id)

    # Test the KSeF request ----------------------------------------------------

    @freeze_time('2026-03-15 12:00:00')
    def test_request_date_types(self):
        """ The batch export filters by the day KSeF stored the invoice, up to
            its high water mark
        """
        with (
            patch.object(KsefApiServiceBatch, '_create_encryption_data', return_value=self.encryption_data),
            self._mock_ksef({'referenceNumber': '20260315-EX-1'}) as mock_request,
        ):
            batch = self.Batch._create_batch_download(self.company, datetime(2026, 3, 8), datetime(2026, 3, 15, 12))
        mock_request.assert_called_once()
        (method, url), kwargs = mock_request.call_args
        self.assertEqual((method, url), ('POST', f'{self.server_url}/invoices/exports'))
        self.assertEqual(kwargs['json'], {
            'encryption': {'encryptedSymmetricKey': 'RU5D', 'initializationVector': 'SVY='},
            'filters': {
                'dateRange': {
                    'dateType': 'PermanentStorage',
                    'from': '2026-03-08T00:00:00.000Z',
                    'to': '2026-03-15T12:00:00.000Z',
                    'restrictToPermanentStorageHwmDate': True,
                },
                'subjectType': 'Subject2',
            },
        })
        self.assertRecordValues(batch, [{'name': '20260315-EX-1', 'state': 'requested'}])

    # Test the autovacuum ------------------------------------------------------

    def test_autovacuum(self):
        done_old_batch = self._create_batch('done_old', {'status': {'code': 200}})
        failed_old_batch = self._create_batch('failed_old', {'status': {'code': 415}})
        failed_old_part = self._add_part(failed_old_batch, 1, content=b'decrypted zip slice')
        done_recent_batch = self._create_batch('done_recent', {'status': {'code': 200}})
        requested_old_batch = self._create_batch('requested_old')

        now = fields.Datetime.now()
        self._set_write_date(done_old_batch | failed_old_batch | requested_old_batch, now - timedelta(days=31))
        self._set_write_date(done_recent_batch, now - timedelta(days=29))
        self.Batch._gc_batch_downloads()

        self.assertEqual(
            (done_recent_batch | requested_old_batch | done_old_batch | failed_old_batch).exists(),
            done_recent_batch | requested_old_batch,
        )
        self.assertFalse(failed_old_part.exists())

    # Test the install and uninstall -------------------------------------------

    def test_install_turns_off_single_download_cron(self):
        single_download_cron = self.env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')

        # At install, the noupdate data turns off the single bill download
        single_download_cron.active = True
        convert_file(self.env, 'l10n_pl_edi_batch', 'data/ir_cron_data.xml', {}, mode='init')
        self.assertFalse(single_download_cron.active)

        # At uninstall, the single bill download takes over again
        single_download_cron.active = False
        uninstall_hook(self.env)
        self.assertTrue(single_download_cron.active)

    # Test the today cron ------------------------------------------------------

    def test_cron_today_windows(self):
        now = fields.Datetime.start_of(fields.Datetime.now(), 'day') + timedelta(hours=10)
        yesterday = ksef_midnight(now.date() - timedelta(days=1))

        # Every run asks for yesterday 00:00 to now
        with freeze_time(now), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        first_batch = self._company_batches(self.company)
        self.assertRecordValues(first_batch, [{'date_from': yesterday, 'date_to': now, 'kind': 'today', 'state': 'requested'}])

        # A batch still in progress: the next run requests nothing
        with freeze_time(now + timedelta(hours=3)), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        self.assertEqual(self._company_batches(self.company), first_batch)

        # Once it failed, neither done nor in progress, the next run asks again from where the first one started
        first_batch.content = {'status': {'code': 415}}
        with freeze_time(now + timedelta(hours=3)), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        second_batch = self._company_batches(self.company) - first_batch
        self.assertRecordValues(second_batch, [{'date_from': yesterday, 'date_to': now + timedelta(hours=3)}])

        # The next day too: no day is skipped while none succeeds
        second_batch.content = {'status': {'code': 415}}
        next_day = now + timedelta(days=1)
        with freeze_time(next_day), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        next_day_batch = self._company_batches(self.company) - first_batch - second_batch
        self.assertRecordValues(next_day_batch, [{'date_from': yesterday, 'date_to': next_day}])

    def test_cron_today_from_last_storage_date(self):
        now = fields.Datetime.start_of(fields.Datetime.now(), 'day') + timedelta(hours=10)
        hwm = now - timedelta(hours=1)
        last_storage = now - timedelta(hours=2)
        with freeze_time(now):
            done_batch = self._create_batch('done', {
                'status': {'code': 200},
                'package': {'parts': [], 'permanentStorageHwmDate': hwm.isoformat() + '+00:00'},
            })
            done_batch.date_to = now

        # After a done today batch, the next run starts from its high water mark
        with freeze_time(now), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        next_batch = self._company_batches(self.company) - done_batch
        self.assertRecordValues(next_batch, [{'date_from': hwm, 'date_to': now}])

        # After a truncated one, from where its export stopped
        next_batch.unlink()
        done_batch.content = {
            'status': {'code': 200},
            'package': {
                'parts': [],
                'isTruncated': True,
                'lastPermanentStorageDate': last_storage.isoformat() + '+00:00',
                'permanentStorageHwmDate': hwm.isoformat() + '+00:00',
            },
        }
        with freeze_time(now), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        next_batch = self._company_batches(self.company) - done_batch
        self.assertRecordValues(next_batch, [{'date_from': last_storage, 'date_to': now}])

        # After an outage of days, still from where the last done batch stopped
        next_batch.unlink()
        outage_end = now + timedelta(days=3)
        with freeze_time(outage_end), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        next_batch = self._company_batches(self.company) - done_batch
        self.assertRecordValues(next_batch, [{'date_from': last_storage, 'date_to': outage_end}])

        # After a done batch where KSeF had nothing yet (420), from that batch's start
        next_batch.unlink()
        done_batch.content = {'status': {'code': 420}}
        with freeze_time(outage_end), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        next_batch = self._company_batches(self.company) - done_batch
        self.assertRecordValues(next_batch, [{'date_from': done_batch.date_from, 'date_to': outage_end}])

    def test_cron_today_errors(self):
        now = fields.Datetime.now().replace(microsecond=0)

        # A KSeF error is logged, and the next run tries again
        with (
            freeze_time(now),
            self._mock_batch_requests(failing_companies=self.company),
            mute_logger('odoo.addons.l10n_pl_edi_batch.models.batch_download'),
        ):
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        self.assertFalse(self._company_batches(self.company))

        # Rate-limited: nothing requested, the cron runs again after the delay KSeF asks for
        with freeze_time(now), self._mock_batch_requests(rate_limited=True):
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        self.assertFalse(self._company_batches(self.company))
        self.assertIn(now + timedelta(seconds=30), self._search_triggers_by_cron('request_today'))

    def test_first_today_request_sets_historic_date(self):
        now = fields.Datetime.now().replace(microsecond=0)
        self.company.l10n_pl_edi_batch_historic_date = False

        # Until the first today request, the history waits
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertFalse(self._company_batches(self.company))

        # The first today request sets the history's end where it starts, and starts the history in 5 minutes
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_today()
        first_batch = self._company_batches(self.company)
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, now.date() - timedelta(days=1))
        self.assertEqual(first_batch.date_from, ksef_midnight(self.company.l10n_pl_edi_batch_historic_date))
        self.assertIn(now + HISTORIC_REQUEST_DELAY, self._search_triggers_by_cron('request_historic'))

        # The next ones leave it alone
        first_batch.content = {'status': {'code': 420}}
        self.company.l10n_pl_edi_batch_historic_date = date(2026, 2, 10)
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_today()
        self.assertEqual(len(self._company_batches(self.company)), 2)
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, date(2026, 2, 10))

    # Test the historic cron ---------------------------------------------------

    def test_cron_historic_windows(self):
        now = fields.Datetime.now().replace(microsecond=0)
        yesterday = now.date() - timedelta(days=1)

        # The first window ends yesterday, and the historic date moves back to its start
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        first_batch = self._company_batches(self.company)
        self.assertRecordValues(first_batch, [{
            'date_from': ksef_midnight(yesterday - timedelta(days=7)),
            'date_to': ksef_midnight(yesterday),
            'kind': 'historic',
            'state': 'requested',
        }])
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, yesterday - timedelta(days=7))

        # In progress: nothing new
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertEqual(self._company_batches(self.company), first_batch)

        # Failed: the same window is requested again
        first_batch.content = {'status': {'code': 415}}
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        second_batch = self._company_batches(self.company) - first_batch
        self.assertRecordValues(second_batch, [{
            'date_from': ksef_midnight(yesterday - timedelta(days=7)),
            'date_to': ksef_midnight(yesterday),
        }])

        # The last window stops at the day KSeF 2.0 went live, then there's nothing left to request
        second_batch.content = {'status': {'code': 200}}
        self.company.l10n_pl_edi_batch_historic_date = date(2026, 2, 3)
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        last_batch = self._company_batches(self.company) - first_batch - second_batch
        self.assertRecordValues(last_batch, [{
            'date_from': ksef_midnight(date(2026, 1, 31)),
            'date_to': ksef_midnight(date(2026, 2, 3)),
        }])
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, date(2026, 1, 31))

        last_batch.content = {'status': {'code': 200}}
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertEqual(self._company_batches(self.company), first_batch | second_batch | last_batch)

    def test_cron_historic_last_window_failed(self):
        now = fields.Datetime.now().replace(microsecond=0)
        self.company.l10n_pl_edi_batch_historic_date = date(2026, 2, 3)

        # The last window is requested: the history reaches the day KSeF became mandatory
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        last_window = self._company_batches(self.company)
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, date(2026, 1, 31))

        # It fails: it is requested again all the same
        last_window.content = {'status': {'code': 415}}
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertRecordValues(self._company_batches(self.company) - last_window, [{
            'date_from': last_window.date_from,
            'date_to': last_window.date_to,
            'state': 'requested',
        }])

    def test_cron_historic_walks_past_fetched_bills(self):
        now = fields.Datetime.now().replace(microsecond=0)
        self._create_single_download_bill('20260205', 'fetched')
        self.company.l10n_pl_edi_batch_historic_date = date(2026, 2, 10)

        # Bills fetched by the single-invoice download don't stop the walk: it goes down to the first KSeF day
        self.assertEqual(self._run_historic_cron(now).date_from, ksef_midnight(date(2026, 2, 3)))
        self.assertEqual(self._run_historic_cron(now).date_from, ksef_midnight(date(2026, 1, 31)))
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, date(2026, 1, 31))
        self.assertFalse(self._run_historic_cron(now))

    def test_cron_request_historic_failed_window(self):
        failed_batches = self.Batch.concat(*(self._create_batch(f'failed-{n}', {'status': {'code': 415}}) for n in range(8)))
        window = {'date_from': failed_batches[0].date_from, 'date_to': failed_batches[0].date_to}

        # The last historic window failed 8 times: it is requested a 9th time
        with self._mock_batch_requests():
            self.Batch._cron_request_historic()
        last_attempt = self._company_batches(self.company) - failed_batches
        self.assertRecordValues(last_attempt, [{**window, 'state': 'requested'}])

        # It fails a 9th time: the error is logged, and the walk goes on with the next window
        last_attempt.content = {'status': {'code': 415}}
        historic_date = self.company.l10n_pl_edi_batch_historic_date
        with self._mock_batch_requests(), self.assertLogs('odoo.addons.l10n_pl_edi_batch.models.batch_download', 'ERROR'):
            self.Batch._cron_request_historic()
        next_batch = self._company_batches(self.company) - failed_batches - last_attempt
        self.assertRecordValues(next_batch, [{
            'date_from': ksef_midnight(historic_date - timedelta(days=7)),
            'date_to': ksef_midnight(historic_date),
        }])

    # Test the status cron -----------------------------------------------------

    def test_cron_check_status(self):
        now = fields.Datetime.now().replace(microsecond=0)

        # A new batch has its status checked right away
        with freeze_time(now), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        requested_batch = self._company_batches(self.company)
        self.assertIn(now, self._search_triggers_by_cron('check_status'))

        # Still 100: one more retry, checked again after 10 * 2**retry_count seconds
        with freeze_time(now), self._mock_ksef({'status': {'code': 100}}):
            self.Batch._cron_check_status()
        self.assertRecordValues(requested_batch, [{'state': 'requested', 'retry_count': 1}])
        self.assertIn(now + exp_backoff_delay(1), self._search_triggers_by_cron('check_status'))

        # 200: the parts are created, the retries start again from 0, and the download starts
        with freeze_time(now), self._mock_ksef(self._ready_answer(now)):
            self.Batch._cron_check_status()
        self.assertRecordValues(requested_batch, [{'state': 'downloading', 'retry_count': 0}])
        self.assertEqual(len(requested_batch.part_ids), 1)
        self.assertIn(now, self._search_triggers_by_cron('download'))

    def test_cron_check_status_next_requested_batch(self):
        now = fields.Datetime.now().replace(microsecond=0)
        today_batch = self._create_batch('today')
        historic_batch = self._create_batch('historic')
        historic_batch.write({'date_from': now - timedelta(days=9), 'date_to': now - timedelta(days=2)})
        today_batch.write({'date_from': now - timedelta(days=1), 'date_to': now})
        ready_answer = self._ready_answer(now)

        # The latest batch is ready: the status of the next requested one is checked right away
        with freeze_time(now), self._mock_ksef(ready_answer):
            self.Batch._cron_check_status()
        self.assertEqual(today_batch.state, 'downloading')
        self.assertEqual(historic_batch.state, 'requested')
        self.assertIn(now, self._search_triggers_by_cron('check_status'))

        with freeze_time(now), self._mock_ksef(ready_answer):
            self.Batch._cron_check_status()
        self.assertEqual(historic_batch.state, 'downloading')

    def test_cron_check_status_retries(self):
        now = fields.Datetime.now().replace(microsecond=0)
        requested_batch = self._create_batch('requested')

        # KSeF unreachable: counted as a retry, and checked again later
        with (
            freeze_time(now),
            patch('odoo.addons.l10n_pl_edi.tools.ksef_api_service.requests.request', side_effect=requests.ConnectionError),
            mute_logger('odoo.addons.l10n_pl_edi.tools.ksef_api_service', 'odoo.addons.l10n_pl_edi_batch.models.batch_download'),
        ):
            self.Batch._cron_check_status()
        self.assertRecordValues(requested_batch, [{'state': 'requested', 'retry_count': 1}])

        # Still 100 after the last retry: the batch fails
        requested_batch.retry_count = 9
        with freeze_time(now), self._mock_ksef({'status': {'code': 100}}):
            self.Batch._cron_check_status()
        self.assertRecordValues(requested_batch, [{'state': 'failed', 'retry_count': 10}])

    def test_cron_check_status_ksef_error(self):
        now = fields.Datetime.now().replace(microsecond=0)
        requested_batch = self._create_batch('requested')

        # A KSeF error fails the batch, and its window is requested again
        with freeze_time(now), self._mock_ksef({'status': {'code': 415}}), self._mock_batch_requests():
            self.Batch._cron_check_status()
        self.assertEqual(requested_batch.state, 'failed')
        self._assert_requested_again(requested_batch, now)

    def test_cron_check_status_truncated(self):
        now = fields.Datetime.now().replace(microsecond=0)
        historic_batch = self._create_batch('historic')
        historic_batch.write({'date_from': datetime(2026, 3, 1), 'date_to': datetime(2026, 3, 8)})
        self._set_write_date(historic_batch, now - timedelta(seconds=10))
        truncated_answer = self._ready_answer(now, isTruncated=True, lastPermanentStorageDate='2026-03-05T10:00:00+00:00')

        # A truncated export is downloaded as it is: its rest is requested only once its bills are imported
        with freeze_time(now), self._mock_ksef(truncated_answer), self._mock_batch_requests():
            self.Batch._cron_check_status()
        self.assertRecordValues(historic_batch, [{'date_to': datetime(2026, 3, 8), 'state': 'downloading'}])
        self.assertEqual(self._company_batches(self.company), historic_batch)

    def test_cron_check_status_nothing_new(self):
        now = fields.Datetime.now().replace(microsecond=0)
        requested_batch = self._create_batch('requested')
        self._set_write_date(requested_batch, now - timedelta(seconds=10))

        # KSeF has stored nothing after the window's start yet: the batch is done, isn't requested again, and the history moves on
        with freeze_time(now), self._mock_ksef({'status': {'code': 420}}), self._mock_batch_requests():
            self.Batch._cron_check_status()
        self.assertEqual(requested_batch.state, 'done')
        self.assertEqual(self._company_batches(self.company), requested_batch)
        self.assertIn(now + HISTORIC_REQUEST_DELAY, self._search_triggers_by_cron('request_historic'))

    # Test the download cron ---------------------------------------------------

    def test_cron_download(self):
        now = fields.Datetime.now().replace(microsecond=0)
        downloading_batch = self._create_downloading_batch(now=now)
        mock_decrypt, mock_request = self._mock_part_downloads()

        # One part per run
        with freeze_time(now), mock_decrypt, mock_request:
            self.Batch._cron_download()
        self.assertEqual(downloading_batch.part_ids.mapped(lambda part: bool(part.decrypted_file)), [True, False])
        self.assertEqual(downloading_batch.state, 'downloading')

        mock_decrypt, mock_request = self._mock_part_downloads()
        with freeze_time(now), mock_decrypt, mock_request:
            self.Batch._cron_download()
        self.assertEqual(downloading_batch.part_ids.mapped(lambda part: bool(part.decrypted_file)), [True, True])
        self.assertEqual(downloading_batch.state, 'downloaded')
        self.assertEqual(base64.b64decode(downloading_batch.part_ids[1].decrypted_file), b'slice')
        self.assertIn(now, self._search_triggers_by_cron('import'))

    def test_cron_download_failures(self):
        now = fields.Datetime.now().replace(microsecond=0)
        downloading_batch = self._create_downloading_batch(part_count=1, now=now)
        error = requests.HTTPError("503 Service Unavailable")

        # A failed download counts a retry, and the batch is tried again after 10 * 2**retry_count seconds
        mock_decrypt, mock_request = self._mock_part_downloads(error)
        with freeze_time(now), mock_decrypt, mock_request:
            self.Batch._cron_download()
        self.assertRecordValues(downloading_batch, [{'state': 'downloading', 'retry_count': 1}])
        self.assertIn(now + exp_backoff_delay(1), self._search_triggers_by_cron('download'))

        # After the last retry, the batch fails with the download error, and its window is requested again
        downloading_batch.retry_count = 9
        mock_decrypt, mock_request = self._mock_part_downloads(error)
        with freeze_time(now), mock_decrypt, mock_request, self._mock_batch_requests():
            self.Batch._cron_download()
        self.assertEqual(downloading_batch.state, 'failed')
        self.assertTrue(downloading_batch.error.startswith("999: Odoo Error\nCouldn't download KSeF batch part downloading_batch-001.zip.aes"))
        self._assert_requested_again(downloading_batch, now)

    # Test the import cron -----------------------------------------------------

    def test_cron_import(self):
        now = fields.Datetime.now().replace(microsecond=0)
        today_batch = self._create_downloaded_batch('today', now)
        historic_batch = self._create_downloaded_batch('historic', now, historic=True)
        historic_triggers_before = self._search_triggers_by_cron('request_historic')

        # One batch per run, today batches first; a today batch doesn't move the history on
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertEqual(today_batch.state, 'done')
        self.assertEqual(historic_batch.state, 'downloaded')
        self.assertEqual(self._search_triggers_by_cron('request_historic'), historic_triggers_before)

        # A historic batch done: the historic cron requests the next window in 5 minutes
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertEqual(historic_batch.state, 'done')
        self.assertIn(now + HISTORIC_REQUEST_DELAY, self._search_triggers_by_cron('request_historic'))
        bills = self.env['account.move'].search([('l10n_pl_edi_number', 'in', ('today-ksef-number', 'historic-ksef-number'))])
        self.assertEqual(len(bills), 2)

    def test_cron_import_truncated_batch_rest(self):
        """ Once the bills of a truncated export are in, the rest is requested
            from where KSeF stopped, up to the end of the same window.
        """
        now = fields.Datetime.now().replace(microsecond=0)
        today_batch = self._create_downloaded_batch('today', now)
        historic_batch = self._create_downloaded_batch('historic', now, historic=True)
        for batch, last_storage in ((today_batch, now - timedelta(hours=2)), (historic_batch, now - timedelta(days=5))):
            batch.content = {**batch.content, 'package': {
                'isTruncated': True,
                'lastPermanentStorageDate': last_storage.isoformat() + '+00:00',
            }}
        historic_triggers_before = self._search_triggers_by_cron('request_historic')

        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_import()
            self.Batch._cron_import()
        rest_batches = self._company_batches(self.company) - today_batch - historic_batch
        self.assertRecordValues(rest_batches, [
            {'date_from': now - timedelta(hours=2), 'date_to': now, 'kind': 'today', 'state': 'requested'},
            {'date_from': now - timedelta(days=5), 'date_to': now - timedelta(days=2), 'kind': 'historic', 'state': 'requested'},
        ])
        # the history doesn't move on while the window isn't complete
        self.assertEqual(self._search_triggers_by_cron('request_historic'), historic_triggers_before)

    def test_cron_import_time_budget(self):
        now = fields.Datetime.now().replace(microsecond=0)
        zip_bytes = self._make_zip({f'budget-{number}-ksef-number.xml': self.xml_content for number in range(3)})
        batch = self._create_batch('budget', {'status': {'code': 200}})
        batch.write({'date_from': now - timedelta(days=9), 'date_to': now - timedelta(days=2)})
        self._add_zip_parts(batch, zip_bytes, count=2)

        # No time left: each run imports one bill, and triggers the import again for the rest
        with patch('odoo.addons.l10n_pl_edi_batch.models.batch_download.IMPORT_SECONDS', 0), freeze_time(now):
            for imported in (1, 2):
                self.Batch._cron_import()
                bills = self.env['account.move'].search([('l10n_pl_edi_number', 'like', 'budget-%-ksef-number')])
                self.assertEqual(len(bills), imported)
                self.assertEqual(batch.state, 'downloaded')
                self.assertIn(now, self._search_triggers_by_cron('import'))

            # The last bill: the batch is done, and the history moves on
            self.Batch._cron_import()
        bills = self.env['account.move'].search([('l10n_pl_edi_number', 'like', 'budget-%-ksef-number')])
        self.assertEqual(len(bills), 3)
        self.assertEqual(batch.state, 'done')
        self.assertIn(now + HISTORIC_REQUEST_DELAY, self._search_triggers_by_cron('request_historic'))

    # Test end to end ----------------------------------------------------------

    def test_crons_end_to_end(self):
        now = fields.Datetime.now().replace(microsecond=0)
        zip_bytes = self._make_zip({'end-to-end-ksef-number.xml': self.xml_content, '_metadata.json': '{}'})

        # Request: the today cron asks KSeF for the window, and schedules the first status check
        with freeze_time(now), self._mock_batch_requests():
            self.env['l10n_pl_edi_batch.download']._cron_request_today()
        batch = self._company_batches(self.company)
        self.assertEqual(batch.state, 'requested')
        self.assertIn(now, self._search_triggers_by_cron('check_status'))

        # Status: KSeF has the package ready, in one part
        self._set_write_date(batch, now - timedelta(seconds=10))
        with freeze_time(now), self._mock_ksef(self._ready_answer(now)):
            self.Batch._cron_check_status()
        self.assertEqual(batch.state, 'downloading')
        self.assertIn(now, self._search_triggers_by_cron('download'))

        # Download: the part is fetched and decrypted
        self._set_write_date(batch, now - timedelta(seconds=10))
        mock_decrypt, mock_request = self._mock_part_downloads(content=zip_bytes)
        with freeze_time(now), mock_decrypt, mock_request:
            self.Batch._cron_download()
        self.assertEqual(batch.state, 'downloaded')
        self.assertIn(now, self._search_triggers_by_cron('import'))

        # Import: the bill is created from its XML, and the batch is done
        self._set_write_date(batch, now - timedelta(seconds=10))
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertEqual(batch.state, 'done')
        bill = self.env['account.move'].search([('l10n_pl_edi_number', '=', 'end-to-end-ksef-number')])
        self.assertTrue(bill.invoice_line_ids)
        self.assertTrue(self._search_xml_from_bill(bill))

    # Test the UI --------------------------------------------------------------

    def test_import_from_ksef_requests_today_batch(self):
        other_company = self.setup_other_company()['company']
        other_company.l10n_pl_edi_access_token = 'other token'
        self.company.l10n_pl_edi_batch_historic_date = False

        # An accountant asks for the latest bills: a today batch for their company only, the batch crons do the rest
        AccountMove = self.env['account.move'].with_user(self.simple_accountman).with_company(self.company)
        with self._mock_batch_requests():
            action = AccountMove.action_l10n_pl_edi_import_from_ksef()
        self.assertEqual(action['params'], {'type': 'success', 'message': "Bills requested from KSeF."})
        self.assertRecordValues(self._company_batches(self.company), [{'kind': 'today', 'state': 'requested'}])
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, fields.Date.today() - timedelta(days=1))
        self.assertFalse(self._company_batches(other_company))

        # A second click while that batch is in progress requests nothing
        with self._mock_batch_requests():
            action = AccountMove.action_l10n_pl_edi_import_from_ksef()
        self.assertEqual(action['params'], {'type': 'info', 'message': "Bills were just requested from KSeF."})
        self.assertEqual(len(self._company_batches(self.company)), 1)

    def test_import_from_ksef_while_cron_runs(self):
        # Stand-in for the crons' row locks, without the database: one holder at a time, refused at once like NOWAIT
        locks = defaultdict(threading.Lock)

        def try_lock(crons, lockfk=False):
            if not locks[crons.id].acquire(blocking=False):
                raise UserError("Locked")

        request_today_lock = locks[self.env.ref('l10n_pl_edi_batch.ir_cron_request_today').id]
        AccountMove = self.env['account.move'].with_company(self.company)
        with patch.object(self.env.registry['ir.cron'], '_try_lock', try_lock), self._mock_batch_requests():
            # The "request recent bills" cron is running: the click requests nothing
            request_today_lock.acquire()
            action = AccountMove.action_l10n_pl_edi_import_from_ksef()
            self.assertEqual(action['params'], {'type': 'info', 'message': "Bills were just requested from KSeF."})
            self.assertFalse(self._company_batches(self.company))

            # Once it's done, the click requests the bills
            request_today_lock.release()
            action = AccountMove.action_l10n_pl_edi_import_from_ksef()
            self.assertEqual(action['params'], {'type': 'success', 'message': "Bills requested from KSeF."})
            self.assertEqual(len(self._company_batches(self.company)), 1)

    def test_import_from_ksef_cooldown(self):
        now = fields.Datetime.now().replace(microsecond=0)
        AccountMove = self.env['account.move'].with_company(self.company)

        # A click requests the bills, and KSeF has nothing new: the batch is done at once
        with freeze_time(now), self._mock_batch_requests():
            AccountMove.action_l10n_pl_edi_import_from_ksef()
        first_batch = self._company_batches(self.company)
        first_batch.content = {'status': {'code': 420}}

        # Just before the delay is over, nothing is requested again
        with freeze_time(now + TODAY_REQUEST_DELAY - timedelta(minutes=1)), self._mock_batch_requests():
            action = AccountMove.action_l10n_pl_edi_import_from_ksef()
        self.assertEqual(action['params'], {'type': 'info', 'message': "Bills were just requested from KSeF."})
        self.assertEqual(self._company_batches(self.company), first_batch)

        # Once it's over, it is
        with freeze_time(now + TODAY_REQUEST_DELAY + timedelta(minutes=1)), self._mock_batch_requests():
            action = AccountMove.action_l10n_pl_edi_import_from_ksef()
        self.assertEqual(action['params'], {'type': 'success', 'message': "Bills requested from KSeF."})
        self.assertEqual(len(self._company_batches(self.company)), 2)
