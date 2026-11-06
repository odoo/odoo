import base64
import io
import zipfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import requests

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import freeze_time, tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService
from odoo.addons.l10n_pl_edi_batch.models.batch_part import BatchDownloadPart
from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlEdiBatch(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.Batch = cls.env['l10n_pl_edi_batch.download']
        cls.env['ir.config_parameter'].sudo().set_param('l10n_pl_edi_ksef.mode', 'test')

    def _mock_ksef(self, json_answer):
        """ Stands in for KSeF: every request gets a 200 with `json_answer`; returns the mock, to read the requests sent. """
        response = MagicMock(status_code=200)
        response.json.return_value = json_answer
        return patch('odoo.addons.l10n_pl_edi.tools.ksef_api_service.requests.request', return_value=response)

    def _create_batch(self, name, content=None):
        return self.Batch.create({
            'name': name,
            'company_id': self.company.id,
            'date_from': '2026-11-01 00:00:00',
            'date_to': '2026-11-08 00:00:00',
            'content': content,
        })

    @freeze_time('2026-11-10 12:00:00')
    def test_date_expiry_from_content(self):
        requested_batch = self._create_batch('requested')
        ready_batch = self._create_batch('ready', {
            'status': {'code': 200},
            # Warsaw time (UTC+1): 13:00 UTC
            'packageExpirationDate': '2026-11-12T14:00:00+01:00',
        })
        expired_batch = self._create_batch('expired', {
            'status': {'code': 200},
            'packageExpirationDate': '2026-11-09T12:00:00+00:00',
        })
        rejected_batch = self._create_batch('rejected', {'status': {'code': 415}})

        self.assertFalse(requested_batch.date_expiry)
        self.assertFalse(requested_batch.is_expired)

        self.assertEqual(ready_batch.date_expiry, datetime(2026, 11, 12, 13, 0, 0))
        self.assertFalse(ready_batch.is_expired)

        self.assertTrue(expired_batch.is_expired)

        batches = requested_batch | ready_batch | expired_batch | rejected_batch
        self.assertEqual(self.Batch.search([('is_expired', '=', True)]) & batches, expired_batch)
        self.assertEqual(self.Batch.search([('is_expired', '=', False)]) & batches, requested_batch | ready_batch | rejected_batch)

    def test_errors_from_content(self):
        ready_batch = self._create_batch('ready', {
            'status': {'code': 200, 'description': "Eksport zakonczony"},
            'package': {'invoiceCount': 3},
        })
        rejected_batch = self._create_batch('rejected', {
            'status': {'code': 415, 'description': "Blad odszyfrowania", 'details': ["Bad key"]},
        })

        # KSeF's own errors come from its answer; a successful batch has none
        self.assertFalse(ready_batch.error)
        self.assertEqual(rejected_batch.error, "415: Blad odszyfrowania\nBad key")

        # Our own errors are written in the same place, with code 999, keeping the rest of the answer
        ready_batch._set_odoo_error("Corrupt ZIP")
        self.assertEqual(ready_batch.state, 'failed')
        self.assertEqual(ready_batch.error, "999: Odoo Error\nCorrupt ZIP")
        self.assertEqual(ready_batch.content['package'], {'invoiceCount': 3})

    def test_kind(self):
        # No frozen time: `create_date` comes from the database clock, which freeze_time doesn't change
        now = fields.Datetime.now()
        historic_batch = self.Batch.create({
            'name': 'historic',
            'company_id': self.company.id,
            'date_from': now - timedelta(days=9),
            'date_to': now - timedelta(days=2),
        })
        today_batch = self.Batch.create({
            'name': 'today',
            'company_id': self.company.id,
            'date_from': now - timedelta(days=1),
            'date_to': now,
        })

        self.assertEqual(historic_batch.kind, 'historic')
        self.assertEqual(today_batch.kind, 'today')
        self.assertEqual(today_batch.retry_count, 0)
        batches = historic_batch | today_batch
        self.assertEqual(self.Batch.search([('kind', '=', 'historic')]) & batches, historic_batch)
        self.assertEqual(self.Batch.search([('kind', '!=', 'historic')]) & batches, today_batch)

    def _add_zip_parts(self, batch, zip_bytes, count=2):
        """ Cut the ZIP in `count` slices, as KSeF does, and store them as downloaded parts. """
        size = -(-len(zip_bytes) // count)
        parts = self.env['l10n_pl_edi_batch.part'].create([
            {
                'batch_id': batch.id,
                'part_number': number + 1,
                'download_method': 'GET',
                'download_url': f'https://ksef.test/{batch.name}-{number + 1:03}.zip.aes',
            }
            for number in range(count)
        ])
        for number, part in enumerate(parts):
            part._store_decrypted_file(zip_bytes[number * size:(number + 1) * size])
        return parts

    def test_parts_decrypted_file(self):
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        Part = self.env['l10n_pl_edi_batch.part']
        first_part = self._add_part(ready_batch, 1, downloaded=True)
        second_part = self._add_part(ready_batch, 2, downloaded=False)

        # No attachment exists before the download
        part_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', Part._name),
            ('res_field', '=', 'decrypted_file'),
            ('res_id', 'in', (first_part | second_part).ids),
        ])
        self.assertEqual(len(part_attachments), 1)
        with self.assertRaises(UserError):
            ready_batch.import_bills()

        # The parts' files are attachments of the parts, deleted with them
        ready_batch.unlink()
        self.assertFalse(part_attachments.exists())

    def test_import_bills(self):
        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            xml_content = xml_file.read()
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('new-ksef-number.xml', xml_content)
            zip_file.writestr('known-ksef-number.xml', xml_content)
            zip_file.writestr('_metadata.json', '{}')

        known_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'l10n_pl_edi_number': 'known-ksef-number',
        })
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, zip_stream.getvalue())
        self.assertEqual(ready_batch.state, 'downloaded')

        bills_before = self.env['account.move'].search([('move_type', '=', 'in_invoice')])
        ready_batch.import_bills()
        new_bill = self.env['account.move'].search([('move_type', '=', 'in_invoice')]) - bills_before

        # One bill for the new KSeF number, with its XML; the known one is skipped
        self.assertEqual(new_bill.l10n_pl_edi_number, 'new-ksef-number')
        self.assertEqual(new_bill.l10n_pl_edi_status, 'fetched')
        self.assertEqual(new_bill.l10n_pl_edi_attachment_id.name, 'new-ksef-number.xml')
        self.assertEqual(new_bill.l10n_pl_edi_attachment_id.raw, xml_content)
        self.assertTrue(known_bill.exists())
        self.assertFalse(ready_batch.part_ids)
        self.assertEqual(ready_batch.state, 'done')

        # Nothing left to import: a second call does nothing
        ready_batch.import_bills()
        self.assertEqual(self.env['account.move'].search([('move_type', '=', 'in_invoice')]) - bills_before, new_bill)

    def test_import_bills_corrupt_zip(self):
        now = fields.Datetime.now().replace(microsecond=0)
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})

        # The parts are downloaded again, once the batch is due
        self._add_zip_parts(ready_batch, b'not a zip at all')
        with freeze_time(now):
            ready_batch.import_bills()
        self.assertRecordValues(ready_batch, [{'state': 'downloading', 'retry_count': 1}])
        self.assertFalse(any(ready_batch.part_ids.with_context(bin_size=True).mapped('decrypted_file')))
        self.assertIn(now + timedelta(seconds=20), self._cron_triggers('l10n_pl_edi_batch.ir_cron_download'))

        # After the last retry, the batch fails
        ready_batch.part_ids.unlink()
        self._add_zip_parts(ready_batch, b'not a zip at all')
        ready_batch.retry_count = 9
        ready_batch.import_bills()
        self.assertEqual(ready_batch.state, 'failed')
        self.assertTrue(ready_batch.error.startswith("999: Odoo Error\nThe KSeF batch ZIP is corrupt"))

    def _add_part(self, batch, number, downloaded):
        values = {
            'batch_id': batch.id,
            'part_number': number,
            'download_method': 'GET',
            'download_url': f'https://ksef.test/part-{number:03}.zip.aes',
        }
        if downloaded:
            values['decrypted_file'] = base64.b64encode(b'decrypted zip slice')
        return self.env['l10n_pl_edi_batch.part'].create(values)

    @freeze_time('2026-11-10 12:00:00')
    def test_state(self):
        ready = {'status': {'code': 200}, 'packageExpirationDate': '2026-11-12T12:00:00+00:00'}
        expired = {'status': {'code': 200}, 'packageExpirationDate': '2026-11-09T12:00:00+00:00'}

        requested_batch = self._create_batch('requested')

        rejected_batch = self._create_batch('rejected', {'status': {'code': 415}})
        odoo_error_batch = self._create_batch('odoo_error', ready)
        odoo_error_batch._set_odoo_error("Corrupt ZIP")
        too_many_retries_batch = self._create_batch('too_many_retries')
        too_many_retries_batch.retry_count = 10
        expired_missing_part_batch = self._create_batch('expired_missing_part', expired)
        self._add_part(expired_missing_part_batch, 1, downloaded=False)

        downloading_batch = self._create_batch('downloading', ready)
        self._add_part(downloading_batch, 1, downloaded=True)
        self._add_part(downloading_batch, 2, downloaded=False)

        downloaded_batch = self._create_batch('downloaded', ready)
        self._add_part(downloaded_batch, 1, downloaded=True)
        # Expiry doesn't matter once all the parts are downloaded
        expired_downloaded_batch = self._create_batch('expired_downloaded', expired)
        self._add_part(expired_downloaded_batch, 1, downloaded=True)

        # Imported, or nothing to download: no parts left
        done_batch = self._create_batch('done', ready)
        empty_batch = self._create_batch('empty', {'status': {'code': 200}, 'package': {'invoiceCount': 0}})

        failed_batches = rejected_batch | odoo_error_batch | too_many_retries_batch | expired_missing_part_batch
        expected_states = {
            'requested': requested_batch,
            'failed': failed_batches,
            'downloading': downloading_batch,
            'downloaded': downloaded_batch | expired_downloaded_batch,
            'done': done_batch | empty_batch,
        }
        batches = self.Batch.union(*expected_states.values())
        for state, expected_batches in expected_states.items():
            for batch in expected_batches:
                self.assertEqual(batch.state, state, batch.name)
            self.assertEqual(self.Batch.search([('state', '=', state)]) & batches, expected_batches, state)
        self.assertEqual(self.Batch.search([('state', 'not in', ['done', 'failed'])]) & batches,
                         requested_batch | downloading_batch | downloaded_batch | expired_downloaded_batch)

    @freeze_time('2026-03-15 12:00:00')
    def test_request_date_types(self):
        # The batch export filters by the day KSeF received the invoice, as the single-invoice download does
        encryption_data = {'raw_symmetric_key': 'S0VZ', 'encrypted_symmetric_key': 'RU5D', 'raw_iv': 'SVY='}
        with (
            patch.object(KsefApiServiceBatch, '_create_encryption_data', return_value=encryption_data),
            self._mock_ksef({'referenceNumber': '20260315-EX-1'}) as mock_request,
        ):
            batch = self.Batch._request(self.company, datetime(2026, 3, 8), datetime(2026, 3, 15, 12))
        mock_request.assert_called_once()
        (method, url), kwargs = mock_request.call_args
        self.assertEqual((method, url), ('POST', 'https://api-test.ksef.mf.gov.pl/v2/invoices/exports'))
        self.assertEqual(kwargs['json'], {
            'encryption': {'encryptedSymmetricKey': 'RU5D', 'initializationVector': 'SVY='},
            'filters': {
                'dateRange': {
                    'dateType': 'Invoicing',
                    'from': '2026-03-08T00:00:00.000Z',
                    'to': '2026-03-15T12:00:00.000Z',
                },
                'subjectType': 'Subject2',
            },
        })
        self.assertRecordValues(batch, [{'name': '20260315-EX-1', 'state': 'requested'}])

        # The single-invoice download of l10n_pl_edi filters by Invoicing too
        with self._mock_ksef({'invoices': [], 'hasMore': False}) as mock_request:
            self.env['account.move'].with_company(self.company)._fetch_bills_metadata(KsefApiService(self.company))
        mock_request.assert_called_once()
        (method, url), kwargs = mock_request.call_args
        self.assertEqual((method, url), ('POST', 'https://api-test.ksef.mf.gov.pl/v2/invoices/query/metadata'))
        self.assertEqual(kwargs['params'], {'pageSize': 200, 'pageOffset': 0})
        self.assertEqual(kwargs['json'], {
            'subjectType': 'Subject2',
            'dateRange': {
                'from': '2026-01-31T00:00:00',
                'to': '2026-03-16T12:00:00',
                'dateType': 'Invoicing',
            },
        })

    def test_gc_batch_downloads(self):
        done_old_batch = self._create_batch('done_old', {'status': {'code': 200}})
        failed_old_batch = self._create_batch('failed_old', {'status': {'code': 415}})
        failed_old_part = self._add_part(failed_old_batch, 1, downloaded=True)
        done_recent_batch = self._create_batch('done_recent', {'status': {'code': 200}})
        requested_old_batch = self._create_batch('requested_old')

        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE l10n_pl_edi_batch_download SET write_date = now() at time zone 'UTC' - interval '31 days' WHERE id IN %s",
            [(done_old_batch | failed_old_batch | requested_old_batch)._ids],
        )
        self.env.cr.execute(
            "UPDATE l10n_pl_edi_batch_download SET write_date = now() at time zone 'UTC' - interval '29 days' WHERE id = %s",
            [done_recent_batch.id],
        )
        self.env.invalidate_all()

        self.Batch._gc_batch_downloads()
        self.assertFalse(done_old_batch.exists())
        self.assertFalse(failed_old_batch.exists())
        self.assertFalse(failed_old_part.exists())
        self.assertTrue(done_recent_batch.exists())
        self.assertTrue(requested_old_batch.exists())

    def _mock_batch_requests(self, failing_companies=(), rate_limited=False):
        """ Stands in for the KSeF export request: a new reference number per call, unless the company fails or
            KSeF is rate-limited. """
        encryption_data = {'raw_symmetric_key': 'S0VZ', 'encrypted_symmetric_key': 'RU5D', 'raw_iv': 'SVY='}
        numbers = iter(range(1, 1000))

        def download_batch_request(service, date_from, date_to, encryption_data):
            if rate_limited:
                raise KSeFRateLimitError("Too Many Requests", retry_after=30)
            if service.company in failing_companies:
                raise UserError("KSeF API Error: 500")
            return {'referenceNumber': f'{service.company.name}-{next(numbers)}'}

        return patch.multiple(
            KsefApiServiceBatch,
            _create_encryption_data=lambda service: encryption_data,
            download_batch_request=download_batch_request,
        )

    def _enable_batches(self, *companies):
        self.env['ir.config_parameter'].sudo().set_param('l10n_pl_edi_batch.enabled', 'True')
        for company in companies:
            company.sudo().l10n_pl_edi_access_token = 'token'

    def _company_batches(self, company):
        return self.Batch.search([('company_id', '=', company.id)], order='id')

    def test_cron_today_windows(self):
        self._enable_batches(self.company)
        now = fields.Datetime.start_of(fields.Datetime.now(), 'day') + timedelta(hours=10)
        yesterday = fields.Datetime.start_of(now, 'day') - timedelta(days=1)

        # The first batch of the day starts yesterday 00:00
        with freeze_time(now), self._mock_batch_requests():
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        first_batch = self._company_batches(self.company)
        self.assertRecordValues(first_batch, [{
            'date_from': yesterday,
            'date_to': now,
            'kind': 'today',
            'state': 'requested',
        }])

        # Still requested: nothing new
        with freeze_time(now + timedelta(hours=3)), self._mock_batch_requests():
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        self.assertEqual(self._company_batches(self.company), first_batch)

        # Done: the next one follows it, with a 1-hour overlap
        first_batch.content = {'status': {'code': 200}}
        with freeze_time(now + timedelta(hours=3)), self._mock_batch_requests():
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        second_batch = self._company_batches(self.company) - first_batch
        self.assertRecordValues(second_batch, [{
            'date_from': now - timedelta(hours=1),
            'date_to': now + timedelta(hours=3),
            'state': 'requested',
        }])

        # Failed: its window is requested again
        second_batch.content = {'status': {'code': 415}}
        with freeze_time(now + timedelta(hours=6)), self._mock_batch_requests():
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        third_batch = self._company_batches(self.company) - first_batch - second_batch
        self.assertRecordValues(third_batch, [{
            'date_from': now - timedelta(hours=1),
            'date_to': now + timedelta(hours=6),
        }])

        # The first batch of the next day starts at its yesterday 00:00 again
        third_batch.content = {'status': {'code': 200}}
        next_day = now + timedelta(days=1)
        with freeze_time(next_day), self._mock_batch_requests():
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        next_day_batch = self._company_batches(self.company) - first_batch - second_batch - third_batch
        self.assertRecordValues(next_day_batch, [{'date_from': yesterday + timedelta(days=1), 'date_to': next_day}])

    def test_cron_today_errors(self):
        other_company = self.setup_other_company(name='company_2')['company']
        self._enable_batches(self.company, other_company)
        now = fields.Datetime.now().replace(microsecond=0)

        # A KSeF error skips its company only
        with (
            freeze_time(now),
            self._mock_batch_requests(failing_companies=self.company),
            self.assertLogs('odoo.addons.l10n_pl_edi_batch.models.batch_download', 'ERROR'),
        ):
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        self.assertFalse(self._company_batches(self.company))
        self.assertEqual(len(self._company_batches(other_company)), 1)

        # Rate-limited: nothing requested, the cron runs again after the delay KSeF asks for
        cron = self.env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')
        with freeze_time(now), self._mock_batch_requests(rate_limited=True):
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        self.assertFalse(self._company_batches(self.company))
        triggers = self.env['ir.cron.trigger'].search([('cron_id', '=', cron.id)])
        self.assertIn(now + timedelta(seconds=30), triggers.mapped('call_at'))

    def test_cron_today_disabled(self):
        self._enable_batches(self.company)
        self.env['ir.config_parameter'].sudo().set_param('l10n_pl_edi_batch.enabled', 'False')
        AccountMove = type(self.env['account.move'])
        with (
            self._mock_batch_requests(),
            patch.object(AccountMove, '_l10n_pl_edi_download_bills_from_ksef', return_value=False) as single_download,
        ):
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        single_download.assert_called()
        self.assertFalse(self._company_batches(self.company))

    def test_cron_historic_windows(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        yesterday = fields.Datetime.start_of(now, 'day') - timedelta(days=1)

        # The first window ends yesterday, and the historic date moves back to its start
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        first_batch = self._company_batches(self.company)
        self.assertRecordValues(first_batch, [{
            'date_from': yesterday - timedelta(days=7),
            'date_to': yesterday,
            'kind': 'historic',
            'state': 'requested',
        }])
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, yesterday - timedelta(days=7))

        # In progress: nothing new
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertEqual(self._company_batches(self.company), first_batch)

        # Failed: the next window comes anyway
        first_batch.content = {'status': {'code': 415}}
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        second_batch = self._company_batches(self.company) - first_batch
        self.assertRecordValues(second_batch, [{
            'date_from': yesterday - timedelta(days=14),
            'date_to': yesterday - timedelta(days=7),
        }])

        # The last window stops at the day KSeF 2.0 went live, then there's nothing left to request
        second_batch.content = {'status': {'code': 200}}
        self.company.l10n_pl_edi_batch_historic_date = datetime(2026, 2, 3)
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        last_batch = self._company_batches(self.company) - first_batch - second_batch
        self.assertRecordValues(last_batch, [{
            'date_from': datetime(2026, 1, 31),
            'date_to': datetime(2026, 2, 3),
        }])
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, datetime(2026, 1, 31))

        last_batch.content = {'status': {'code': 200}}
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertEqual(self._company_batches(self.company), first_batch | second_batch | last_batch)

    def test_cron_historic_errors(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)

        # A failed request doesn't move the historic date
        with (
            freeze_time(now),
            self._mock_batch_requests(failing_companies=self.company),
            self.assertLogs('odoo.addons.l10n_pl_edi_batch.models.batch_download', 'ERROR'),
        ):
            self.Batch._cron_request_historic()
        self.assertFalse(self._company_batches(self.company))
        self.assertFalse(self.company.l10n_pl_edi_batch_historic_date)

        # Disabled: nothing requested
        self.env['ir.config_parameter'].sudo().set_param('l10n_pl_edi_batch.enabled', 'False')
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        self.assertFalse(self._company_batches(self.company))

    def _set_write_date(self, batch, write_date):
        self.env.flush_all()
        self.env.cr.execute("UPDATE l10n_pl_edi_batch_download SET write_date = %s WHERE id = %s", [write_date, batch.id])
        batch.invalidate_recordset(['write_date'])

    def _cron_triggers(self, xmlid):
        cron = self.env.ref(xmlid)
        return self.env['ir.cron.trigger'].search([('cron_id', '=', cron.id)]).mapped('call_at')

    def test_cron_check_status(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        cron_xmlid = 'l10n_pl_edi_batch.ir_cron_check_status'

        # A new batch is checked once due, 10 s after its request
        with freeze_time(now), self._mock_batch_requests():
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        requested_batch = self._company_batches(self.company)
        self.assertIn(now + timedelta(seconds=10), self._cron_triggers(cron_xmlid))

        # Not due yet: KSeF isn't asked
        self._set_write_date(requested_batch, now - timedelta(seconds=5))
        with freeze_time(now), self._mock_ksef({'status': {'code': 100}}) as mock_request:
            self.Batch._cron_check_status()
        mock_request.assert_not_called()

        # Still 100: one more retry, checked again once due
        self._set_write_date(requested_batch, now - timedelta(seconds=10))
        with freeze_time(now), self._mock_ksef({'status': {'code': 100}}):
            self.Batch._cron_check_status()
        self.assertRecordValues(requested_batch, [{'state': 'requested', 'retry_count': 1}])
        self.assertIn(now + timedelta(seconds=20), self._cron_triggers(cron_xmlid))

        # 200: the parts are created and the retries start again from 0
        self._set_write_date(requested_batch, now - timedelta(seconds=20))
        ready_answer = {
            'status': {'code': 200},
            'packageExpirationDate': (now + timedelta(days=1)).isoformat() + '+00:00',
            'package': {'parts': [{'ordinalNumber': 1, 'url': 'https://ksef.test/part-001.zip.aes', 'method': 'get'}]},
        }
        with freeze_time(now), self._mock_ksef(ready_answer):
            self.Batch._cron_check_status()
        self.assertRecordValues(requested_batch, [{'state': 'downloading', 'retry_count': 0}])
        self.assertEqual(len(requested_batch.part_ids), 1)
        self.assertIn(now, self._cron_triggers('l10n_pl_edi_batch.ir_cron_download'))

    def test_cron_check_status_retries_used_up(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        cron_xmlid = 'l10n_pl_edi_batch.ir_cron_check_status'
        requested_batch = self._create_batch('requested')
        requested_batch.retry_count = 9
        self._set_write_date(requested_batch, now - timedelta(seconds=10 * 2 ** 9))
        triggers_before = self._cron_triggers(cron_xmlid)

        # The 10th retry fails the batch, and nothing more is scheduled for it
        with freeze_time(now), self._mock_ksef({'status': {'code': 100}}):
            self.Batch._cron_check_status()
        self.assertRecordValues(requested_batch, [{'state': 'failed', 'retry_count': 10}])
        self.assertEqual(self._cron_triggers(cron_xmlid), triggers_before)

    def _mock_part_downloads(self, error=None, content=b'slice'):
        """ Stands in for the storage of the parts: each one decrypts to `content`, unless the download fails. """
        response = MagicMock(status_code=200)
        if error:
            response.raise_for_status.side_effect = error
        return patch.multiple(
            BatchDownloadPart,
            _decrypt_stream=lambda part, response: iter([content]),
        ), patch('odoo.addons.l10n_pl_edi_batch.models.batch_part.requests.request', return_value=response)

    def _create_downloading_batch(self, now, part_count=2):
        batch = self._create_batch('downloading', {
            'status': {'code': 200},
            'packageExpirationDate': (now + timedelta(days=1)).isoformat() + '+00:00',
        })
        for number in range(1, part_count + 1):
            self._add_part(batch, number, downloaded=False)
        self._set_write_date(batch, now - timedelta(seconds=10))
        return batch

    def test_cron_download(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        downloading_batch = self._create_downloading_batch(now)
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
        self.assertIn(now, self._cron_triggers('l10n_pl_edi_batch.ir_cron_import'))

    def test_cron_download_failures(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        downloading_batch = self._create_downloading_batch(now, part_count=1)
        error = requests.HTTPError("503 Service Unavailable")

        # A failed download counts a retry, and the batch is tried again once due
        mock_decrypt, mock_request = self._mock_part_downloads(error)
        with freeze_time(now), mock_decrypt, mock_request, self.assertLogs('odoo.addons.l10n_pl_edi_batch', 'WARNING'):
            self.Batch._cron_download()
        self.assertRecordValues(downloading_batch, [{'state': 'downloading', 'retry_count': 1}])
        self.assertIn(now + timedelta(seconds=20), self._cron_triggers('l10n_pl_edi_batch.ir_cron_download'))

        # After the last retry, the batch fails with the download error
        downloading_batch.retry_count = 9
        self._set_write_date(downloading_batch, now - timedelta(seconds=10 * 2 ** 9))
        mock_decrypt, mock_request = self._mock_part_downloads(error)
        with freeze_time(now), mock_decrypt, mock_request, self.assertLogs('odoo.addons.l10n_pl_edi_batch', 'WARNING'):
            self.Batch._cron_download()
        self.assertEqual(downloading_batch.state, 'failed')
        self.assertTrue(downloading_batch.error.startswith("999: Odoo Error\nCouldn't download KSeF batch part part-001.zip.aes"))

    def _create_downloaded_batch(self, name, now, historic=False):
        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            xml_content = xml_file.read()
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'{name}-ksef-number.xml', xml_content)
        batch = self._create_batch(name, {'status': {'code': 200}})
        if historic:
            batch.date_to = now - timedelta(days=2)
        self._add_zip_parts(batch, zip_stream.getvalue(), count=1)
        self._set_write_date(batch, now - timedelta(seconds=10))
        return batch

    def test_cron_import(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        today_batch = self._create_downloaded_batch('today', now)
        historic_batch = self._create_downloaded_batch('historic', now, historic=True)
        historic_cron_xmlid = 'l10n_pl_edi_batch.ir_cron_request_historic'
        historic_triggers_before = self._cron_triggers(historic_cron_xmlid)

        # One batch per run, today batches first; a today batch doesn't move the history on
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertEqual(today_batch.state, 'done')
        self.assertEqual(historic_batch.state, 'downloaded')
        self.assertEqual(self._cron_triggers(historic_cron_xmlid), historic_triggers_before)

        # A historic batch done: the historic cron requests the next window
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertEqual(historic_batch.state, 'done')
        self.assertIn(now, self._cron_triggers(historic_cron_xmlid))
        bills = self.env['account.move'].search([('l10n_pl_edi_number', 'in', ('today-ksef-number', 'historic-ksef-number'))])
        self.assertEqual(len(bills), 2)

    def test_import_bills_bad_xmls(self):
        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            xml_content = xml_file.read()
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('unreadable-ksef-number.xml', b'<not xml')
            zip_file.writestr('failing-ksef-number.xml', xml_content)
            zip_file.writestr('good-ksef-number.xml', xml_content)
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, zip_stream.getvalue())

        AccountMove = type(self.env['account.move'])
        decode_fa3_ksef = AccountMove._decode_fa3_ksef

        def failing_decoder(move, invoice, file_data, new=False):
            if file_data['filename'] == 'failing-ksef-number.xml':
                raise ValueError("Unexpected tag")
            return decode_fa3_ksef(move, invoice, file_data, new)

        # The standard import catches the errors of each XML, and goes on with the next one
        with (
            patch.object(AccountMove, '_decode_fa3_ksef', failing_decoder),
            self.assertLogs('odoo.addons.account.models.account_move', 'ERROR'),
        ):
            ready_batch.import_bills()
        bills = self.env['account.move'].search([('l10n_pl_edi_number', 'like', '%-ksef-number')])
        bills_by_number = {bill.l10n_pl_edi_number: bill for bill in bills}
        self.assertEqual(ready_batch.state, 'done')
        self.assertTrue(bills_by_number['good-ksef-number'].invoice_line_ids)
        for number in ('unreadable-ksef-number', 'failing-ksef-number'):
            bill = bills_by_number[number]
            self.assertFalse(bill.invoice_line_ids, number)
            self.assertEqual(bill.l10n_pl_edi_attachment_id.name, f'{number}.xml')
        failing_messages = bills_by_number['failing-ksef-number'].message_ids.mapped('body')
        self.assertTrue(any("Error importing attachment" in body for body in failing_messages))

    def test_list_buttons_trigger_the_crons(self):
        now = fields.Datetime.now().replace(microsecond=0)
        buttons = {
            'action_trigger_check_status': 'l10n_pl_edi_batch.ir_cron_check_status',
            'action_trigger_download': 'l10n_pl_edi_batch.ir_cron_download',
            'action_trigger_import': 'l10n_pl_edi_batch.ir_cron_import',
        }
        # A plain internal user, without access to the crons, can use the buttons
        user = self.env['res.users'].create({
            'name': 'KSeF user',
            'login': 'ksef_user',
            'groups_id': [Command.set([self.env.ref('base.group_user').id])],
            'company_id': self.company.id,
            'company_ids': [Command.set([self.company.id])],
        })
        for method, cron_xmlid in buttons.items():
            with freeze_time(now):
                getattr(self.Batch.with_user(user), method)()
            self.assertIn(now, self._cron_triggers(cron_xmlid), method)

    def test_cron_check_status_truncated_historic(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        historic_batch = self._create_batch('historic')
        historic_batch.write({'date_from': datetime(2026, 3, 1), 'date_to': datetime(2026, 3, 8)})
        self._set_write_date(historic_batch, now - timedelta(seconds=10))
        truncated_answer = {
            'status': {'code': 200},
            'packageExpirationDate': (now + timedelta(days=1)).isoformat() + '+00:00',
            'package': {
                'isTruncated': True,
                'lastInvoicingDate': '2026-03-05T10:00:00+00:00',
                'parts': [{'ordinalNumber': 1, 'url': 'https://ksef.test/part-001.zip.aes', 'method': 'get'}],
            },
        }

        # The batch ends where its package does, and the rest of its window is requested right away
        with freeze_time(now), self._mock_ksef(truncated_answer), self._mock_batch_requests():
            self.Batch._cron_check_status()
        self.assertRecordValues(historic_batch, [{'date_to': datetime(2026, 3, 5, 10), 'state': 'downloading'}])
        rest_batch = self._company_batches(self.company) - historic_batch
        self.assertRecordValues(rest_batch, [{
            'date_from': datetime(2026, 3, 5, 10),
            'date_to': datetime(2026, 3, 8),
            'kind': 'historic',
            'state': 'requested',
        }])

    def test_crons_end_to_end(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            xml_content = xml_file.read()
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('end-to-end-ksef-number.xml', xml_content)
            zip_file.writestr('_metadata.json', '{}')

        # Request: the today cron asks KSeF for the window, and schedules the first status check
        with freeze_time(now), self._mock_batch_requests():
            self.env['account.move']._cron_l10n_pl_edi_download_bills()
        batch = self._company_batches(self.company)
        self.assertEqual(batch.state, 'requested')
        self.assertIn(now + timedelta(seconds=10), self._cron_triggers('l10n_pl_edi_batch.ir_cron_check_status'))

        # Status: KSeF has the package ready, in one part
        ready_answer = {
            'status': {'code': 200},
            'packageExpirationDate': (now + timedelta(days=1)).isoformat() + '+00:00',
            'package': {'parts': [{'ordinalNumber': 1, 'url': 'https://ksef.test/part-001.zip.aes', 'method': 'get'}]},
        }
        self._set_write_date(batch, now - timedelta(seconds=10))
        with freeze_time(now), self._mock_ksef(ready_answer):
            self.Batch._cron_check_status()
        self.assertEqual(batch.state, 'downloading')
        self.assertIn(now, self._cron_triggers('l10n_pl_edi_batch.ir_cron_download'))

        # Download: the part is fetched and decrypted
        self._set_write_date(batch, now - timedelta(seconds=10))
        mock_decrypt, mock_request = self._mock_part_downloads(content=zip_stream.getvalue())
        with freeze_time(now), mock_decrypt, mock_request:
            self.Batch._cron_download()
        self.assertEqual(batch.state, 'downloaded')
        self.assertIn(now, self._cron_triggers('l10n_pl_edi_batch.ir_cron_import'))

        # Import: the bill is created from its XML, and the batch is done
        self._set_write_date(batch, now - timedelta(seconds=10))
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertEqual(batch.state, 'done')
        bill = self.env['account.move'].search([('l10n_pl_edi_number', '=', 'end-to-end-ksef-number')])
        self.assertTrue(bill.invoice_line_ids)
        self.assertEqual(bill.l10n_pl_edi_attachment_id.name, 'end-to-end-ksef-number.xml')

    def _create_single_download_bill(self, day, status):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'l10n_pl_edi_number': f'5265877635-{day}-010080-DD2B5E-{status[:2]}',
            'l10n_pl_edi_status': status,
        })

    def _run_historic_cron(self, now):
        """ One run of the historic cron; the batch it requests is then done, so that the next run moves on. """
        batches_before = self._company_batches(self.company)
        with freeze_time(now), self._mock_batch_requests():
            self.Batch._cron_request_historic()
        new_batch = self._company_batches(self.company) - batches_before
        new_batch.content = {'status': {'code': 200}}
        return new_batch

    def test_cron_historic_stops_at_fetched_bill(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        self._create_single_download_bill('20260501', 'fetched')
        self._create_single_download_bill('20260502', 'fetched')
        self.company.l10n_pl_edi_batch_historic_date = datetime(2026, 5, 10)

        # Down to the window holding a fetched bill, and the history ends
        self.assertEqual(self._run_historic_cron(now).date_from, datetime(2026, 5, 3))
        self.assertEqual(self._run_historic_cron(now).date_from, datetime(2026, 4, 26))
        self.assertEqual(self.company.l10n_pl_edi_batch_historic_date, datetime(2026, 1, 31))
        self.assertFalse(self._run_historic_cron(now))

    def test_import_from_ksef_fills_half_fetched_bills(self):
        self._enable_batches(self.company)
        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            xml_content = xml_file.read()
        half_fetched_bills = self._create_single_download_bill('20260501', 'fetch_ready')
        half_fetched_bills |= self._create_single_download_bill('20260502', 'fetch_failed')
        AccountMove = type(self.env['account.move'])

        # Only the half-fetched bills are downloaded, by KSeF number: no metadata query for new bills
        with (
            patch.object(KsefApiService, 'get_invoice_by_ksef_number', return_value={'xml_content': xml_content}) as get_invoice,
            patch.object(AccountMove, '_fetch_bills_metadata') as fetch_metadata,
        ):
            self.env['account.move'].with_company(self.company).action_l10n_pl_edi_import_from_ksef()
        fetch_metadata.assert_not_called()
        self.assertEqual(get_invoice.call_count, 2)
        self.assertEqual(half_fetched_bills.mapped('l10n_pl_edi_status'), ['fetched', 'fetched'])

        # Disabled: the single-invoice download, as before
        self.env['ir.config_parameter'].sudo().set_param('l10n_pl_edi_batch.enabled', 'False')
        with patch.object(AccountMove, '_l10n_pl_edi_download_bills_from_ksef') as single_download:
            self.env['account.move'].with_company(self.company).action_l10n_pl_edi_import_from_ksef()
        single_download.assert_called_once()

    def test_setting_enables_batches(self):
        settings = self.env['res.config.settings'].create({'l10n_pl_edi_batch_enabled': True})
        settings.execute()
        self.assertTrue(self.Batch._is_enabled())
        settings = self.env['res.config.settings'].create({'l10n_pl_edi_batch_enabled': False})
        settings.execute()
        self.assertFalse(self.Batch._is_enabled())

    def test_crons_end_to_end_historic(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        yesterday = fields.Datetime.start_of(now, 'day') - timedelta(days=1)
        historic_cron_xmlid = 'l10n_pl_edi_batch.ir_cron_request_historic'
        ksef_number = f"5265877635-{(yesterday - timedelta(days=3)).strftime('%Y%m%d')}-010080-DD2B5E-26"
        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            xml_content = xml_file.read()
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'{ksef_number}.xml', xml_content)

        # Request: the historic cron asks for the week before yesterday
        first_batch = self._run_historic_cron(now)
        first_batch.content = False
        self.assertRecordValues(first_batch, [{'date_from': yesterday - timedelta(days=7), 'kind': 'historic', 'state': 'requested'}])

        # Status, download and import, each cron triggering the next one
        ready_answer = {
            'status': {'code': 200},
            'packageExpirationDate': (now + timedelta(days=1)).isoformat() + '+00:00',
            'package': {'parts': [{'ordinalNumber': 1, 'url': 'https://ksef.test/part-001.zip.aes', 'method': 'get'}]},
        }
        self._set_write_date(first_batch, now - timedelta(seconds=10))
        with freeze_time(now), self._mock_ksef(ready_answer):
            self.Batch._cron_check_status()
        self.assertEqual(first_batch.state, 'downloading')
        self.assertNotIn(now, self._cron_triggers(historic_cron_xmlid))
        self._set_write_date(first_batch, now - timedelta(seconds=10))
        mock_decrypt, mock_request = self._mock_part_downloads(content=zip_stream.getvalue())
        with freeze_time(now), mock_decrypt, mock_request:
            self.Batch._cron_download()
        self.assertEqual(first_batch.state, 'downloaded')
        self.assertNotIn(now, self._cron_triggers(historic_cron_xmlid))
        self._set_write_date(first_batch, now - timedelta(seconds=10))
        with freeze_time(now):
            self.Batch._cron_import()
        self.assertEqual(first_batch.state, 'done')
        self.assertTrue(self.env['account.move'].search([('l10n_pl_edi_number', '=', ksef_number)]))

        # Done: the historic cron runs again right away, for the week before
        self.assertIn(now, self._cron_triggers(historic_cron_xmlid))
        second_batch = self._run_historic_cron(now)
        self.assertEqual(second_batch.date_from, yesterday - timedelta(days=14))

    def test_crons_end_to_end_empty_historic_window(self):
        self._enable_batches(self.company)
        now = fields.Datetime.now().replace(microsecond=0)
        yesterday = fields.Datetime.start_of(now, 'day') - timedelta(days=1)
        historic_cron_xmlid = 'l10n_pl_edi_batch.ir_cron_request_historic'
        first_batch = self._run_historic_cron(now)
        first_batch.content = False

        # No invoice in the window: done at the status check, and the historic cron runs again right away
        self._set_write_date(first_batch, now - timedelta(seconds=10))
        with freeze_time(now), self._mock_ksef({'status': {'code': 200}, 'package': {'invoiceCount': 0, 'parts': []}}):
            self.Batch._cron_check_status()
        self.assertEqual(first_batch.state, 'done')
        self.assertIn(now, self._cron_triggers(historic_cron_xmlid))
        second_batch = self._run_historic_cron(now)
        self.assertEqual(second_batch.date_from, yesterday - timedelta(days=14))

    def test_part_slice_stored_without_mimetype_guess(self):
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('ksef-number.xml', b'<xml/>' * 1000)
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})

        # The first slice starts like a ZIP but isn't a whole one: stored as .zip, its type isn't guessed
        with self.assertNoLogs('odoo.tools.mimetypes', 'WARNING'):
            parts = self._add_zip_parts(ready_batch, zip_stream.getvalue(), count=2)
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'l10n_pl_edi_batch.part'),
            ('res_field', '=', 'decrypted_file'),
            ('res_id', '=', parts[0].id),
        ])
        self.assertRecordValues(attachment, [{'name': 'ready-001.zip', 'mimetype': 'application/zip'}])
        self.assertEqual(ready_batch.state, 'downloaded')
